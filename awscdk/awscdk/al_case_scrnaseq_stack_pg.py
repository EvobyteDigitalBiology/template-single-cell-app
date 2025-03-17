
from aws_cdk import Stack
from aws_cdk import aws_rds as rds
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs

from constructs import Construct


from .al_case_scrnaseq_stack_network import AlCaseScrnaseqStackNetwork

class AlCaseScrnaseqStackPG(Stack):

    def __init__(self, scope: Construct, construct_id: str, cdk_config: dict, network_stack: AlCaseScrnaseqStackNetwork, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        assert 'db_username' in cdk_config, 'db_username not found in cdk_config'
        assert 'db_name' in cdk_config, 'db_name not found in cdk_config'
        
        
        # Define RDS
        
        secret = rds.DatabaseSecret(self,
            "AlCaseScrnaseq-PGSecret",
            username=cdk_config['db_username']
        )

        instance1 = rds.DatabaseInstance(self,
        "AlCaseScrnaseq-PG",
        engine=rds.DatabaseInstanceEngine.postgres(version=rds.PostgresEngineVersion.VER_16_3),
        database_name = cdk_config['db_name'],
        credentials=rds.Credentials.from_secret(secret),
        instance_type = ec2.InstanceType('t3.micro'),
        vpc=network_stack.vpc,
        allocated_storage = 20,
        vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
        security_groups = [network_stack.sg_postgres]
        )
        
        self._rds_endpoint = instance1.db_instance_endpoint_address
        self._rds_secret_key = secret.secret_name
        self._rds_secret_key_arn = secret.secret_arn
        
    @property
    def rds_endpoint(self):
        return self._rds_endpoint
    
    @property
    def rds_secret_key(self):
        return self._rds_secret_key
    
    @property
    def rds_secret_key_arn(self):
        return self._rds_secret_key_arn