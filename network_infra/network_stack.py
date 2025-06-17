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

class NetworkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        
        super().__init__(scope, construct_id, **kwargs)

        
        for vpc_config in config.VPC_LIST:
            vpc = self.create_vpc(
                vpc_config.VPV_ID,
                vpc_config.VPC_NAME,
                vpc_config.INTERNET_GATEWAY,
                vpc_config.VPC_CIDR,
                vpc_config.VPC_MAX_AZS,
                vpc_config.NAT_GATEWAY,
                vpc_config.PUBLIC_SUBNET_CIDR,
                vpc_config.PRIVATE_SUBNET_CIDR,
                vpc_config.ISOLATED_SUBNET_CIDR
            )
        

    
    def create_vpc(self ,identifier ,vpc_name , internet_gateway, vpc_cidr, vpc_maz_azs, nat_gw, public_subnet_cidr, private_subnet_cidr, isolated_subnet_cidr):

        self.vpc = ec2.Vpc(
            self, identifier,
            vpc_name=vpc_name,
            create_internet_gateway=internet_gateway,
            cidr= vpc_cidr,
            max_azs= vpc_maz_azs,
            nat_gateways= nat_gw,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask= public_subnet_cidr
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS, # Instances need egress to download packages
                    cidr_mask= private_subnet_cidr
                ),
                ec2.SubnetConfiguration(
                    name="Isolated",
                    subnet_type=ec2.SubnetType.ISOLATED,
                    cidr_mask= isolated_subnet_cidr
                )
            ]
        )
        Tags.of(self.vpc).add("Name", config.VPC_NAME)


