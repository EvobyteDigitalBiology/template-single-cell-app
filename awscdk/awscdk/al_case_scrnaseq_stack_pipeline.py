from aws_cdk import Stack
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_notifications as s3n
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import aws_iam as iam

from constructs import Construct

from .al_case_scrnaseq_stack_network import AlCaseScrnaseqStackNetwork


class AlCaseScrnaseqStackPipeline(Stack):
    
    def __init__(self, 
                 scope: Construct, 
                 construct_id: str, 
                 cdk_config: dict, 
                 policy_config: dict,
                 network_stack: AlCaseScrnaseqStackNetwork,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        assert 'fastq_registration_task_storage_gb' in cdk_config, 'fastq_registration_task_storage_gb not found in cdk_config'
        assert 'service_user_secret_key_name' in cdk_config, 'service_user_secret_key_name not found in cdk_config'
        assert 'service_user_secret_key_arn' in cdk_config, 'service_user_secret_key_arn not found in cdk_config'
        assert 's3_bucket_bootstrap' in cdk_config, 's3_bucket_bootstrap not found in cdk_config'
        assert 'pipeline_data_bucket' in cdk_config, 'pipeline_data_bucket not found in cdk_config'
        assert 'fastq_registration_input_bucket' in cdk_config, 'fastq_registration_input_bucket not found in cdk_config'
        assert 'fastq_registration_output_prefix' in cdk_config, 'fastq_registration_output_prefix not found in cdk_config'
        
        # CONFIG
        service_user_secret_key_name = cdk_config['service_user_secret_key_name']
        service_user_secret_key_arn = cdk_config['service_user_secret_key_arn']
        s3_bootstrap_bucket = cdk_config['s3_bucket_bootstrap']
        
        fastq_registration_task_storage_gb = int(cdk_config['fastq_registration_task_storage_gb'])
        
        rawdata_processing_task_storage_gb = int(cdk_config['rawdata_processing_task_storage_gb'])
        rawdata_processing_num_cpus = int(cdk_config['rawdata_processing_task_num_cpus'])
        rawdata_processing_task_ram_gb = int(cdk_config['rawdata_processing_task_ram_gb'])
        
        rawdata_processing_num_cpus_aws_format = str(rawdata_processing_num_cpus*1024)
        rawdata_processing_task_ram_gb_aws_format = str(rawdata_processing_task_ram_gb*1024)
        rawdata_processing_task_ram_cellranger = str(rawdata_processing_task_ram_gb-2) # Reduce 2GB for overhead
        
        # integration        
        integration_task_ram_gb = int(cdk_config['integration_task_ram_gb'])
        integration_task_num_cpus = int(cdk_config['integration_task_num_cpus'])
        integration_task_storage_gb = int(cdk_config['integration_task_storage_gb'])
        
        integration_task_ram_gb_aws_format = str(integration_task_ram_gb*1024)
        integration_task_num_cpus_aws_format = str(integration_task_num_cpus*1024)

        # Define secret(s)
        service_user_secret = secretsmanager.Secret.from_secret_complete_arn(self, 'AlCaseScrnaseq-User-Secret', service_user_secret_key_arn)
        
        # Define bucket(s)
        fastq_registration_input_bucket = s3.Bucket.from_bucket_name(self, 'fastq-registration-input-bucket', cdk_config['fastq_registration_input_bucket'])
        pipeline_data_bucket = s3.Bucket.from_bucket_name(self, 'pipeline-data-bucket', cdk_config['pipeline_data_bucket'])
        
        #region fastqregistration
        
        # Define fastq registration task
        fastq_registration_repo = ecr.Repository.from_repository_name(self, 'case-scrnaseq-fastq-registration-repo', 'case-scrnaseq-fastq-registration')
        fastq_registration_image = ecs.EcrImage.from_ecr_repository(fastq_registration_repo)
            
        fastq_registration_task_definition = ecs.TaskDefinition(self,
                                                    'case-scrnaseq-fastq-registration-td',
                                                    compatibility=ecs.Compatibility.FARGATE,
                                                    cpu='1024',
                                                    memory_mib = '2048',
                                                    ephemeral_storage_gib = fastq_registration_task_storage_gb)
        
        fastq_registration_container = fastq_registration_task_definition.add_container(
                'case-scrnaseq-fastq-registration-con',
                image=fastq_registration_image,
                container_name='case-scrnaseq-fastq-registration-con',
                logging=ecs.LogDrivers.aws_logs(stream_prefix='ecs/fastq-registration'),
                environment_files=[ecs.EnvironmentFile.from_asset('assets/fastq_registration.dev.env')],
                environment={
                    'FASTQ_REGISTRATION_SERVICE_USER_SECRET_KEY_NAME' : service_user_secret_key_name,
                }
        )
        
        # ENV File Policy
        fastq_registration_task_execution_role_policy = iam.PolicyStatement.from_json(policy_config['task_execution_role_envfiles'])
        fastq_registration_task_execution_role_policy.add_resources(f'arn:aws:s3:::{s3_bootstrap_bucket}/*', f'arn:aws:s3:::{s3_bootstrap_bucket}')
        
        fastq_registration_task_definition.add_to_execution_role_policy(
            fastq_registration_task_execution_role_policy
        )

        # task role: Secrets, get env file, get input bucket, get/put output bucket
        # Secret
        fastq_registration_task_role_policy_secrets = iam.PolicyStatement.from_json(policy_config['task_execution_role_getsecrets'])
        fastq_registration_task_role_policy_secrets.add_resources(service_user_secret.secret_full_arn)
        
        fastq_registration_task_definition.add_to_task_role_policy(
            fastq_registration_task_role_policy_secrets
        )
        
        # .env file
        fastq_registration_task_definition.add_to_task_role_policy(
            fastq_registration_task_execution_role_policy
        )
        
        # input bucket
        fastq_registration_input_policy = iam.PolicyStatement.from_json(policy_config['task_execution_role_envfiles'])
        fastq_registration_input_policy.add_resources(f'{fastq_registration_input_bucket.bucket_arn}/*', 
                                                      fastq_registration_input_bucket.bucket_arn)
        
        fastq_registration_task_definition.add_to_task_role_policy(
            fastq_registration_input_policy
        )
        
        # output bucket
        fastq_registration_databucket_policy = iam.PolicyStatement.from_json(policy_config['task_role_s3_io'])
        fastq_registration_databucket_policy.add_resources(f'{pipeline_data_bucket.bucket_arn}/*', 
                                                      pipeline_data_bucket.bucket_arn)
        
        fastq_registration_task_definition.add_to_task_role_policy(
            fastq_registration_databucket_policy
        )
        
        # Logs
        fastq_registration_task_definition.add_to_task_role_policy(
            iam.PolicyStatement.from_json(policy_config['task_cloudwatch_logs'])
        )
        
        # FASTQ Registration Lambda function
        
        # Need to inject sg and tasks into lambda code
        security_groups=network_stack.sg_outbound.security_group_id
        subnets = network_stack.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED).subnet_ids
        subnets = ','.join(subnets)
        
        # # Add lamda function
        fastq_registration_lambda = lambda_.Function(
            self,
            "fastq_registration_lambda",
            runtime = lambda_.Runtime.PYTHON_3_10,
            code = lambda_.Code.from_asset("lambda"),
            handler = "lambda_put_ecs_task.lambda_handler",
            memory_size = 128,
            vpc = network_stack.vpc,
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            environment = {
                'CLUSTER' : network_stack.cluster.cluster_name,
                'TASK_DEFINITION' : fastq_registration_task_definition.family,
                'SECURITY_GROUPS' : security_groups,
                'SUBNETS' : subnets,
                'CONTAINER_OVERRIDES' : fastq_registration_container.container_name,
                'OBJECT_KEY_CMD_ARGUMENT' : '--s3-input-tar-key',
                'BUCKET_CMD_ARGUMENT' : '--s3-bucket'
            }
        )
        
        # Role for lambda: Roles for Task definition, ECR, Task Definition
        fastq_registration_lambda_policy = iam.PolicyStatement.from_json(policy_config['task_role_lambda_run_ecs'])
        
        fastq_registration_lambda_policy.add_resources(fastq_registration_task_definition.task_role.role_arn,
                                                       fastq_registration_task_definition.execution_role.role_arn,
                                                       fastq_registration_repo.repository_arn,
                                                       fastq_registration_task_definition.task_definition_arn,
                                                       'arn:aws:logs:*:*:*')
        
        fastq_registration_lambda.add_to_role_policy(fastq_registration_lambda_policy)
        
        fastq_registration_input_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, 
                                                               s3n.LambdaDestination(fastq_registration_lambda), 
                                                               s3.NotificationKeyFilter(suffix=".tar"))
        
        #endregion fastqregistration

        #region rawdata-processing
        
        # Define fastq registration task
        rawdata_processing_repo = ecr.Repository.from_repository_name(self, 'case-scrnaseq-rawdata-processing-repo', 'case-scrnaseq-rawdata-processing')
        rawdata_processing_image = ecs.EcrImage.from_ecr_repository(rawdata_processing_repo)
                        
        rawdata_processing_task_definition = ecs.TaskDefinition(self,
                                                    'case-scrnaseq-rawdata-processing-td',
                                                    compatibility=ecs.Compatibility.FARGATE,
                                                    cpu=rawdata_processing_num_cpus_aws_format,
                                                    memory_mib = rawdata_processing_task_ram_gb_aws_format,
                                                    ephemeral_storage_gib = rawdata_processing_task_storage_gb)
        
        rawdata_processing_container = rawdata_processing_task_definition.add_container(
                'case-scrnaseq-rawdata-processing-con',
                image=rawdata_processing_image,
                container_name='case-scrnaseq-rawdata-processing-con',
                logging=ecs.LogDrivers.aws_logs(stream_prefix='ecs/rawdata-processing'),
                environment_files=[ecs.EnvironmentFile.from_asset('assets/rawdata_processing.dev.env')],
                environment={
                    'RAWDATA_PROCESSING_SERVICE_USER_SECRET_KEY_NAME' : service_user_secret_key_name,
                    'RAWDATA_PROCESSING_NUM_CORES' : str(rawdata_processing_num_cpus),
                    'RAWDATA_PROCESSING_MEM_GB' : str(rawdata_processing_task_ram_cellranger)
                }
        )
        
        # ENV File Policy
        rawdata_processing_task_execution_role_policy = iam.PolicyStatement.from_json(policy_config['task_execution_role_envfiles'])
        rawdata_processing_task_execution_role_policy.add_resources(f'arn:aws:s3:::{s3_bootstrap_bucket}/*', f'arn:aws:s3:::{s3_bootstrap_bucket}')
        
        rawdata_processing_task_definition.add_to_execution_role_policy(
            rawdata_processing_task_execution_role_policy
        )

        # task role: Secrets, get env file, get input bucket, get/put output bucket
        # Secret
        rawdata_processing_task_role_policy_secrets = iam.PolicyStatement.from_json(policy_config['task_execution_role_getsecrets'])
        rawdata_processing_task_role_policy_secrets.add_resources(service_user_secret.secret_full_arn)
        
        rawdata_processing_task_definition.add_to_task_role_policy(
            rawdata_processing_task_role_policy_secrets
        )
        
        # .env file
        rawdata_processing_task_definition.add_to_task_role_policy(
            rawdata_processing_task_execution_role_policy
        )
        
        # input/output bucket
        rawdata_processing_databucket_policy = iam.PolicyStatement.from_json(policy_config['task_role_s3_io'])
        rawdata_processing_databucket_policy.add_resources(f'{pipeline_data_bucket.bucket_arn}/*', 
                                                            pipeline_data_bucket.bucket_arn)
        
        rawdata_processing_task_definition.add_to_task_role_policy(
            rawdata_processing_databucket_policy
        )
        
        # Logs
        rawdata_processing_task_definition.add_to_task_role_policy(
            iam.PolicyStatement.from_json(policy_config['task_cloudwatch_logs'])
        )
        
        # FASTQ Registration Lambda function
        
        # Need to inject sg and tasks into lambda code
        security_groups=network_stack.sg_outbound.security_group_id
        subnets = network_stack.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED).subnet_ids
        subnets = ','.join(subnets)
        
        # # Add lamda function
        rawdata_processing_lambda = lambda_.Function(
            self,
            "rawdata_processing_lambda",
            runtime = lambda_.Runtime.PYTHON_3_10,
            code = lambda_.Code.from_asset("lambda"),
            handler = "lambda_put_ecs_task.lambda_handler",
            memory_size = 128,
            vpc = network_stack.vpc,
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            environment = {
                'CLUSTER' : network_stack.cluster.cluster_name,
                'TASK_DEFINITION' : rawdata_processing_task_definition.family,
                'SECURITY_GROUPS' : security_groups,
                'SUBNETS' : subnets,
                'CONTAINER_OVERRIDES' : rawdata_processing_container.container_name,
                'OBJECT_KEY_CMD_ARGUMENT' : '--s3-input-key',
                'BUCKET_CMD_ARGUMENT' : '--s3-bucket'
            }
        )
        
        # Role for lambda: Roles for Task definition, ECR, Task Definition
        rawdata_processing_lambda_policy = iam.PolicyStatement.from_json(policy_config['task_role_lambda_run_ecs'])
        
        rawdata_processing_lambda_policy.add_resources(rawdata_processing_task_definition.task_role.role_arn,
                                                       rawdata_processing_task_definition.execution_role.role_arn,
                                                       rawdata_processing_repo.repository_arn,
                                                       rawdata_processing_task_definition.task_definition_arn,
                                                       'arn:aws:logs:*:*:*')
        
        rawdata_processing_lambda.add_to_role_policy(rawdata_processing_lambda_policy)
        
        pipeline_data_bucket.add_event_notification(s3.EventType.OBJECT_CREATED, 
                                                               s3n.LambdaDestination(rawdata_processing_lambda), 
                                                               s3.NotificationKeyFilter(suffix="R2_001.fastq.gz"))
        
        #endregion fastqregistration

        # region integration

        # Define integration task
        integration_repo = ecr.Repository.from_repository_name(self, 'case-scrnaseq-integration-repo', 'case-scrnaseq-integration')
        integration_image = ecs.EcrImage.from_ecr_repository(integration_repo)
                        
        integration_task_definition = ecs.TaskDefinition(self,
                                                    'case-scrnaseq-integration-td',
                                                    compatibility=ecs.Compatibility.FARGATE,
                                                    cpu=integration_task_num_cpus_aws_format,
                                                    memory_mib = integration_task_ram_gb_aws_format,
                                                    ephemeral_storage_gib = integration_task_storage_gb)
        
        integration_container = integration_task_definition.add_container(
                'case-scrnaseq-integration-con',
                image=integration_image,
                container_name='case-scrnaseq-integration-con',
                logging=ecs.LogDrivers.aws_logs(stream_prefix='ecs/integration'),
                environment_files=[ecs.EnvironmentFile.from_asset('assets/integration.dev.env')],
                environment={
                    'INTEGRATION_SERVICE_USER_SECRET_KEY_NAME' : service_user_secret_key_name,
                    'INTEGRATION_MAX_RAM_GB' : str(integration_task_ram_gb)
                }
        )
        
        # ENV File Policy
        integration_task_execution_role_policy = iam.PolicyStatement.from_json(policy_config['task_execution_role_envfiles'])
        integration_task_execution_role_policy.add_resources(f'arn:aws:s3:::{s3_bootstrap_bucket}/*', f'arn:aws:s3:::{s3_bootstrap_bucket}')
        
        integration_task_definition.add_to_execution_role_policy(
            integration_task_execution_role_policy
        )

        # task role: Secrets, get env file, get input bucket, get/put output bucket
        # Secret
        integration_task_role_policy_secrets = iam.PolicyStatement.from_json(policy_config['task_execution_role_getsecrets'])
        integration_task_role_policy_secrets.add_resources(service_user_secret.secret_full_arn)
        
        integration_task_definition.add_to_task_role_policy(
            integration_task_role_policy_secrets
        )
        
        # .env file
        integration_task_definition.add_to_task_role_policy(
            integration_task_execution_role_policy
        )
        
        # input/output bucket
        integration_databucket_policy = iam.PolicyStatement.from_json(policy_config['task_role_s3_io'])
        integration_databucket_policy.add_resources(f'{pipeline_data_bucket.bucket_arn}/*', 
                                                            pipeline_data_bucket.bucket_arn)
        
        integration_task_definition.add_to_task_role_policy(
            integration_databucket_policy
        )
        
        # Logs
        integration_task_definition.add_to_task_role_policy(
            iam.PolicyStatement.from_json(policy_config['task_cloudwatch_logs'])
        )
        
        # integration Lambda function
        
        # Need to inject sg and tasks into lambda code
        security_groups=network_stack.sg_outbound.security_group_id
        subnets = network_stack.vpc.select_subnets(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED).subnet_ids
        subnets = ','.join(subnets)
        
        # # Add lamda function
        integration_lambda = lambda_.Function(
            self,
            "integration_lambda",
            runtime = lambda_.Runtime.PYTHON_3_10,
            code = lambda_.Code.from_asset("lambda"),
            handler = "lambda_put_ecs_task_noargs.lambda_handler",
            memory_size = 128,
            vpc = network_stack.vpc,
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            environment = {
                'CLUSTER' : network_stack.cluster.cluster_name,
                'TASK_DEFINITION' : integration_task_definition.family,
                'SECURITY_GROUPS' : security_groups,
                'SUBNETS' : subnets,
                'CONTAINER_OVERRIDES' : integration_container.container_name,
            }
        )
        
        # Role for lambda: Roles for Task definition, ECR, Task Definition
        integration_lambda_policy = iam.PolicyStatement.from_json(policy_config['task_role_lambda_run_ecs'])
        
        integration_lambda_policy.add_resources(integration_task_definition.task_role.role_arn,
                                                       integration_task_definition.execution_role.role_arn,
                                                       integration_repo.repository_arn,
                                                       integration_task_definition.task_definition_arn,
                                                       'arn:aws:logs:*:*:*')
        
        integration_lambda.add_to_role_policy(integration_lambda_policy)
        
        pipeline_data_bucket.add_event_notification(s3.EventType.OBJECT_CREATED,
                                                               s3n.LambdaDestination(integration_lambda),
                                                               s3.NotificationKeyFilter(suffix="dge.h5", prefix="scrnaseq_dataset"))
        
        #endregion integraton