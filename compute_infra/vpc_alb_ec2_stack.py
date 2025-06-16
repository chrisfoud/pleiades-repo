# vpc_alb_ec2_stack.py
from aws_cdk import (
    Stack,
    Tags,
    CfnOutput,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as targets,
    aws_iam as iam,
)
from constructs import Construct
from . import config

class VpcAlbEc2Stack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        
        super().__init__(scope, construct_id, **kwargs)

        
        
    
    def create_vpc(self):
        # Retrieve configuration from the config file
        app_config = config.AppInfrastructureConfig

        self.vpc = ec2.Vpc(
            self, app_config.VPC.VPC_CFN_ID,
            vpc_name=app_config.VPC.VPC_NAME,
            create_internet_gateway=True,
            cidr="10.0.0.0/16",
            max_azs=app_config.VPC.MAX_AZS,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, # Instances need egress to download packages
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.ISOLATED,
                    cidr_mask=24
                )
            ]
        )
        Tags.of(self.vpc).add("Name", app_config.VPC.VPC_NAME)


