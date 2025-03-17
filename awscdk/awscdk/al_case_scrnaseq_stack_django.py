
from aws_cdk import Stack
from aws_cdk import aws_rds as rds
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_iam as iam
from aws_cdk import aws_s3_assets as s3_assets
from aws_cdk import aws_secretsmanager as secretsmanager
from aws_cdk import Duration

from constructs import Construct



from .al_case_scrnaseq_stack_network import AlCaseScrnaseqStackNetwork
from .al_case_scrnaseq_stack_pg import AlCaseScrnaseqStackPG


class AlCaseScrnaseqStackDjango(Stack):

    def __init__(self,
                 scope: Construct,
                 construct_id: str,
                 cdk_config: dict,
                 policy_config: dict,
                 network_stack: AlCaseScrnaseqStackNetwork,
                 db_stack: AlCaseScrnaseqStackPG,
                 **kwargs) -> None:
        
        super().__init__(scope, construct_id, **kwargs)

        assert 's3_bucket_bootstrap' in cdk_config, 's3_bucket_bootstrap not found in cdk_config'
        assert 'db_name' in cdk_config, 'db_name not found in cdk_config'
        assert 'django_secret_key_arn' in cdk_config, 'django_secret_key_arn not found in cdk_config'
        assert 'service_user_secret_key_arn' in cdk_config, 'service_user_secret_key_arn not found in cdk_config'
        assert 'service_user_healthcheck_secret_key_arn' in cdk_config, 'service_user_healthcheck_secret_key_arn not found in cdk_config'
        assert 'service_user_app_secret_key_arn' in cdk_config, 'service_user_app_secret_key_arn not found in cdk_config'
        
        
        
        
        s3_bootstrap_bucket = cdk_config['s3_bucket_bootstrap']
        
        # Define django secret keys
        django_secret = secretsmanager.Secret.from_secret_complete_arn(self, 'AlCaseScrnaseq-Django-Secret',cdk_config['django_secret_key_arn'])
        service_user_secret = secretsmanager.Secret.from_secret_complete_arn(self, 'AlCaseScrnaseq-User-Secret', cdk_config['service_user_secret_key_arn'])
        service_user_healthcheck_secret = secretsmanager.Secret.from_secret_complete_arn(self, 'AlCaseScrnaseq-User-Healthcheck-Secret', cdk_config['service_user_healthcheck_secret_key_arn'])
        service_user_app_secret = secretsmanager.Secret.from_secret_complete_arn(self, 'AlCaseScrnaseq-User-App-Secret', cdk_config['service_user_app_secret_key_arn'])        
        
        # Upload init script to S3
        django_init_script = s3_assets.Asset(self, 'django_init_script', path='assets/django_init.py')
        
        # Define django task
        django_repo = ecr.Repository.from_repository_name(self, 'case-scrnaseq-django-repo', 'case-scrnaseq-django')
        django_image = ecs.EcrImage.from_ecr_repository(django_repo)
            
        django_task_definition = ecs.TaskDefinition(self,
                                                    'case-scrnaseq-django',
                                                    compatibility=ecs.Compatibility.FARGATE,
                                                    cpu='1024',
                                                    memory_mib = '2048')
        
        django_container = django_task_definition.add_container(
                'django_container',
                image=django_image,
                container_name='case-scrnaseq-django-con',
                port_mappings=[ecs.PortMapping(container_port=8000, host_port=8000)],
                logging=ecs.LogDrivers.aws_logs(stream_prefix='ecs/django'),
                health_check=ecs.HealthCheck(
                    command=["CMD-SHELL", "python3 healthcheck.py"],
                    interval=Duration.seconds(30),
                    retries=3,
                    start_period=Duration.minutes(1),
                    timeout=Duration.seconds(15)),
                environment_files=[ecs.EnvironmentFile.from_asset('assets/django.dev.env')],
                environment={
                    'DB_HOST' : db_stack.rds_endpoint,
                    'DB_NAME' : cdk_config['db_name'],
                    'DB_LOG_SECRET_NAME' : db_stack.rds_secret_key,
                    'DJANGO_INIT_SCRIPT_KEY' : django_init_script.s3_object_key,
                    'DJANGO_INIT_SCRIPT_BUCKET' : s3_bootstrap_bucket
                }
        )
        
        # ENV File Policy
        task_execution_role_policy = iam.PolicyStatement.from_json(policy_config['task_execution_role_envfiles'])
        task_execution_role_policy.add_resources(f'arn:aws:s3:::{s3_bootstrap_bucket}/*', f'arn:aws:s3:::{s3_bootstrap_bucket}')
        
        django_task_definition.add_to_execution_role_policy(
            task_execution_role_policy
        )
        
        # Secrets Policyfor Task Role
        task_role_policy_secrets = iam.PolicyStatement.from_json(policy_config['task_execution_role_getsecrets'])
        task_role_policy_secrets.add_resources(django_secret.secret_full_arn,
                                               service_user_secret.secret_full_arn,
                                               db_stack.rds_secret_key_arn,
                                               service_user_healthcheck_secret.secret_full_arn,
                                               service_user_app_secret.secret_full_arn)
        
        # S3 Policy for Task Role, same as ENV File Policy
        django_task_definition.add_to_task_role_policy(
            task_role_policy_secrets
        )
        django_task_definition.add_to_task_role_policy(
            task_execution_role_policy
        )
        
        # Define service
        ecs.FargateService(
            self,
            id = 'case-scrnaseq-django-service',
            cluster = network_stack.cluster,
            task_definition = django_task_definition,
            vpc_subnets = ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            desired_count = 1,
            cloud_map_options=ecs.CloudMapOptions(
                name="casescrnaseqdjangoservice",
                cloud_map_namespace=network_stack.namespace),
            enable_execute_command = True,
            security_groups = [network_stack.sg_django],
        )