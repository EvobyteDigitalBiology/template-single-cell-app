
from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
import aws_cdk.aws_servicediscovery as sd
import aws_cdk.aws_ecs as ecs

from constructs import Construct


class AlCaseScrnaseqStackNetwork(Stack):

    def __init__(self, scope: Construct, construct_id: str, cdk_config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        assert 'vpc_availbility_zones' in cdk_config, 'vpc_availbility_zones not found in cdk_config'
        assert 'vpc_cidr' in cdk_config, 'vpc_cidr not found in cdk_config'
        
        
        # Define subnets
        public_subnet = ec2.SubnetConfiguration(
            name='AlCaseScrnaseq-Public',
            subnet_type=ec2.SubnetType.PUBLIC,
            cidr_mask=24,
            map_public_ip_on_launch=True
        )
        
        private_subnet = ec2.SubnetConfiguration(
            name='AlCaseScrnaseq-Private',
            subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
            cidr_mask=24
        )
        
        vpc = ec2.Vpc(self,
                    'AlCaseScrnaseq-Vpc',
                    ip_addresses=ec2.IpAddresses.cidr(cdk_config['vpc_cidr']),
                    availability_zones=cdk_config['vpc_availbility_zones'],
                    create_internet_gateway = True,
                    nat_gateways = None,  
                    subnet_configuration = [
                            public_subnet,
                            private_subnet
                    ])
        
        # Define Gateways and Interfaces
        s3_gateway = vpc.add_gateway_endpoint('S3Gateway', service = ec2.GatewayVpcEndpointAwsService.S3)
        ec2_interface = ec2.InterfaceVpcEndpoint(self, 'EC2Interface', vpc = vpc, service = ec2.InterfaceVpcEndpointAwsService.EC2)
        logs_interface = ec2.InterfaceVpcEndpoint(self, 'LogsInterface', vpc = vpc, service = ec2.InterfaceVpcEndpointAwsService.CLOUDWATCH_LOGS)
        ecs_interface = ec2.InterfaceVpcEndpoint(self, 'EcsInterface', vpc = vpc, service = ec2.InterfaceVpcEndpointAwsService.ECS) # Needed for RunECS Task in lambda
        ecr_dkr_interface = ec2.InterfaceVpcEndpoint(self, 'EcrDkrInterface', vpc = vpc, service = ec2.InterfaceVpcEndpointAwsService.ECR_DOCKER)
        ecr_api_interface = ec2.InterfaceVpcEndpoint(self, 'EcrApiInterface', vpc = vpc, service = ec2.InterfaceVpcEndpointAwsService.ECR)
        secrets_manager_interface = ec2.InterfaceVpcEndpoint(self, 'SecretsManagerInterface', vpc = vpc, service = ec2.InterfaceVpcEndpointAwsService.SECRETS_MANAGER)
        
        # Security Groups
        
        sg_postgres = ec2.SecurityGroup(self, 
                                            'SGPostgres',
                                            vpc = vpc)
        
        sg_postgres.add_ingress_rule(
            peer = ec2.Peer.ipv4(cdk_config['vpc_cidr']),
            connection = ec2.Port.tcp(5432)
        )
        
        sg_django = ec2.SecurityGroup(self, 
                                    'SGDjango',
                                    vpc = vpc)
        
        sg_django.add_ingress_rule(
            peer = ec2.Peer.ipv4(cdk_config['vpc_cidr']),
            connection = ec2.Port.tcp(8000)
        )
        
        sg_http = ec2.SecurityGroup(self, 
                                    'SGHttp',
                                    vpc = vpc)
        
        sg_http.add_ingress_rule(
            peer = ec2.Peer.ipv4('0.0.0.0/0'),
            connection = ec2.Port.tcp(80)
        )
        
        sg_https = ec2.SecurityGroup(self, 
                                    'SGHttps',
                                    vpc = vpc)
        
        sg_https.add_ingress_rule(
            peer = ec2.Peer.ipv4('0.0.0.0/0'),
            connection = ec2.Port.tcp(443)
        )
        
        sg_outbound = ec2.SecurityGroup(self, 
                                    'SGOutbound',
                                    vpc = vpc)
        
        # NACLs
        
        private_nacl = ec2.NetworkAcl(self, "AlCaseScrnaseq-Private-NACL",
                                    vpc=vpc,

                                    # the properties below are optional
                                    network_acl_name="AlCaseScrnaseqPrivateNACL",
                                    subnet_selection=ec2.SubnetSelection(
                                        subnet_type=ec2.SubnetType.PRIVATE_ISOLATED
                                    )
                                )
        
        private_nacl.add_entry(
            "AlCaseScrnaseq-Private-Django-Egress",
            rule_number=100,
            cidr=ec2.AclCidr.ipv4(cdk_config['vpc_cidr']),
            traffic=ec2.AclTraffic.tcp_port(8000),
            direction=ec2.TrafficDirection.EGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        private_nacl.add_entry(
            "AlCaseScrnaseq-Private-Django-Ingress",
            rule_number=100,
            cidr=ec2.AclCidr.ipv4(cdk_config['vpc_cidr']),
            traffic=ec2.AclTraffic.tcp_port(8000),
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.ALLOW
        )
    
        # Add NACL config for TCR to be reachable from private subnets
        private_nacl.add_entry(
            "AlCaseScrnaseq-TCP-Egress",
            rule_number=200,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port(443),
            direction=ec2.TrafficDirection.EGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        private_nacl.add_entry(
            "AlCaseScrnaseq-Ephemeral-Egress",
            rule_number=300,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port_range(1024, 65535),
            direction=ec2.TrafficDirection.EGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        private_nacl.add_entry(
            "AlCaseScrnaseq-TCP-Ingress",
            rule_number=200,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port(443),
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        private_nacl.add_entry(
            "AlCaseScrnaseq-Ephemeral-Ingress",
            rule_number=300,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port_range(1024, 65535),
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.ALLOW
        )
                
        # PUBLIC NACL
        
        public_nacl = ec2.NetworkAcl(self, "AlCaseScrnaseq-Public-NACL",
                                    vpc=vpc,
                                    # the properties below are optional
                                    network_acl_name="AlCaseScrnaseqPublicNACL",
                                    subnet_selection=ec2.SubnetSelection(
                                        subnet_type=ec2.SubnetType.PUBLIC
                                    )
                                )
        
        public_nacl.add_entry(
            "AlCaseScrnaseq-Public-NACL-HTTP-Egress",
            rule_number=100,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port(80),
            network_acl_entry_name="AlCaseScrnaseq-Public-NACL-HTTP-Egress",
            direction=ec2.TrafficDirection.EGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        public_nacl.add_entry(
            "AlCaseScrnaseq-Public-NACL-HTTP-Ingress",
            rule_number=100,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port(80),
            network_acl_entry_name="AlCaseScrnaseq-Public-NACL-HTTP-Ingress",
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        public_nacl.add_entry(
            "AlCaseScrnaseq-Public-NACL-HTTPS-Egress",
            rule_number=101,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port(443),
            network_acl_entry_name="AlCaseScrnaseq-Public-NACL-HTTPS-Egress",
            direction=ec2.TrafficDirection.EGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        public_nacl.add_entry(
            "AlCaseScrnaseq-Public-NACL-HTTPS-Ingress",
            rule_number=101,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port(443),
            network_acl_entry_name="AlCaseScrnaseq-Public-NACL-HTTPS-Ingress",
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        public_nacl.add_entry(
            "AlCaseScrnaseq-Public-Ephemeral-Egress",
            rule_number=102,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port_range(1024, 65535),
            direction=ec2.TrafficDirection.EGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        public_nacl.add_entry(
            "AlCaseScrnaseq-Public-Ephemeral-Ingress",
            rule_number=102,
            cidr=ec2.AclCidr.ipv4('0.0.0.0/0'),
            traffic=ec2.AclTraffic.tcp_port_range(1024, 65535),
            direction=ec2.TrafficDirection.INGRESS,
            rule_action=ec2.Action.ALLOW
        )
        
        #Define namespace for Cloud Map Service including DNS Resolution
        namespace = sd.PrivateDnsNamespace(self,
            "alcasescrnaseqnamespace",
            vpc=vpc,
            name="alcasescrnaseqnamespace"
        )
        
        # Define cluster for fargate tasks
        cluster = ecs.Cluster(self, "default", vpc=vpc)

        self._vpc = vpc
        self._sg_postgres = sg_postgres
        self._sg_django = sg_django
        self._sg_http = sg_http
        self._sg_https = sg_https
        self._sg_outbound = sg_outbound
        self._namespace = namespace
        self._cluster = cluster
        
    @property
    def vpc(self):
        return self._vpc
    
    @property
    def sg_postgres(self):
        return self._sg_postgres
    
    @property
    def sg_django(self):
        return self._sg_django
    
    @property
    def sg_http(self):
        return self._sg_http

    @property
    def sg_https(self):
        return self._sg_https
    
    @property
    def sg_outbound(self):
        return self._sg_outbound
    
    @property   
    def namespace(self):
        return self._namespace

    @property
    def cluster(self):
        return self._cluster