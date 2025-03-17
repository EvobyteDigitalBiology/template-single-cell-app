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

class AlCaseScrnaseqStackUI(Stack):
    
    def __init__(self, 
                 scope: Construct, 
                 construct_id: str, 
                 cdk_config: dict, 
                 policy_config: dict,
                 network_stack: AlCaseScrnaseqStackNetwork,
                 **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Load required resources
        assert 'ui_app_task_ram_gb' in cdk_config, 'ui_app_task_ram_gb not found in cdk_config'
        assert 'ui_app_task_num_cpus' in cdk_config, 'ui_app_task_num_cpus not found in cdk_config'
        assert 'ui_app_task_storage_gb' in cdk_config, 'ui_app_task_storage_gb not found in cdk_config'
        assert 'pipeline_data_bucket' in cdk_config, 'pipeline_data_bucket not found in cdk_config'
        
        # UI Resources
        ui_app_task_ram_gb = int(cdk_config['ui_app_task_ram_gb'])
        ui_app_task_num_cpus = int(cdk_config['ui_app_task_num_cpus'])
        ui_app_task_storage_gb = int(cdk_config['ui_app_task_storage_gb'])
        
        assert ui_app_task_storage_gb > 24, 'ui_app_task_storage must be greater than 24 GB'
        
        ui_app_task_ram_gb_aws_format = str(ui_app_task_ram_gb * 1024)
        ui_app_task_num_cpus_aws_format = str(ui_app_task_num_cpus * 1024)
        
        # S3
        pipeline_data_bucket = s3.Bucket.from_bucket_name(self, 'pipeline-data-bucket', cdk_config['pipeline_data_bucket'])
        
        ui_repo = ecr.Repository.from_repository_name(self, 'case-scrnaseq-ui-repo', 'case-scrnaseq-ui')
        ui_nginx_repo = ecr.Repository.from_repository_name(self, 'nginx-case-scrnaseq-ui-repo', 'nginx-case-scrnaseq-ui')
        
        ui_image = ecs.EcrImage.from_ecr_repository(ui_repo)
        ui_nginx_image = ecs.EcrImage.from_ecr_repository(ui_nginx_repo)
        
        ui_app_task_definition = ecs.TaskDefinition(self,
                                                    'case-scrnaseq-ui-td',
                                                    compatibility=ecs.Compatibility.FARGATE,
                                                    cpu=ui_app_task_num_cpus_aws_format,
                                                    memory_mib = ui_app_task_ram_gb_aws_format,
                                                    ephemeral_storage_gib = ui_app_task_storage_gb)
        
        ui_app_container = ui_app_task_definition.add_container(
                'case-scrnaseq-ui-con',
                image=ui_image,
                container_name='case-scrnaseq-ui-con',
                logging=ecs.LogDrivers.aws_logs(stream_prefix='ecs/ui'),
                environment={
                    'BACKEND_API_ENDPOINT' : 'http://casescrnaseqdjangoservice.alcasescrnaseqnamespace:8000/api_v1',
                    'AWS_DEFAULT_REGION' : self.region,
                }
        )
        
        ui_app_nginx_container = ui_app_task_definition.add_container(
                'nginx-case-scrnaseq-ui-con',
                image=ui_nginx_image,
                container_name='nginx-case-scrnaseq-ui-con',
                port_mappings=[ecs.PortMapping(container_port=80, host_port=80),
                               ecs.PortMapping(container_port=443, host_port=443)],
                logging=ecs.LogDrivers.aws_logs(stream_prefix='ecs/ui-nginx')
        )
        
        ui_app_nginx_container.add_container_dependencies(
            ecs.ContainerDependency(
                container=ui_app_container,
                condition=ecs.ContainerDependencyCondition.START
            ))
        
        # HTTP&HTTPS SG
        
        # Permission to download files from integration bucket
        bucket_integration_input_policy = iam.PolicyStatement.from_json(policy_config['task_execution_role_envfiles'])
        bucket_integration_input_policy.add_resources(f'{pipeline_data_bucket.bucket_arn}/scrnaseq_integration/*', 
                                                      f'{pipeline_data_bucket.bucket_arn}/scrnaseq_integration/')
        
        ui_app_task_definition.add_to_task_role_policy(
            bucket_integration_input_policy
        )
        
        ui_app_task_definition.add_to_task_role_policy(
            iam.PolicyStatement.from_json(policy_config['task_cloudwatch_logs'])
        )
        
        # Define fargate service
        ecs.FargateService(
            self,
            id = 'case-scrnaseq-ui-app-service',
            cluster = network_stack.cluster,
            task_definition = ui_app_task_definition,
            assign_public_ip = True,
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            desired_count = 1,
            cloud_map_options=ecs.CloudMapOptions(
                name="casescrnasequiappservice",
                cloud_map_namespace=network_stack.namespace),
            enable_execute_command = True,
            security_groups = [network_stack.sg_http, network_stack.sg_https]
        )