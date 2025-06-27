from aws_cdk import (
    Stack,
    Tags,
    CfnOutput,
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
    aws_elasticloadbalancingv2_targets as targets,
    aws_iam as iam,
    aws_ssm as ssm,
)
from typing import List
from constructs import Construct
from . import config

class NetworkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        
        super().__init__(scope, construct_id, **kwargs)

        for vpc_config in config.VPC_LIST:
            vpc = self.create_vpc(
                vpc_config,
                vpc_config.VPV_ID,
                vpc_config.VPC_NAME,
                vpc_config.VPC_CIDR,
                vpc_config.VPC_MAX_AZS,
                vpc_config.NAT_GATEWAY,
                vpc_config.PUBLIC_SUBNET_MASK,
                vpc_config.PRIVATE_SUBNET_MASK,
                vpc_config.ISOLATED_SUBNET_MASK
            )
            
            # Add CloudFormation outputs for VPC ID
            CfnOutput(
                self, f"{vpc_config.VPV_ID}-id-output",
                value=vpc.vpc_id,
                description=f"VPC ID for {vpc_config.VPC_NAME}",
                export_name=f"{vpc_config.VPC_NAME}-id"
            )
    
    def create_subnet_configurations(self, names: List[str], subnet_type: str, cidr_mask: int) -> List[ec2.SubnetConfiguration]:
        subnet_type_map = {
            'public': ec2.SubnetType.PUBLIC,
            'private': ec2.SubnetType.PRIVATE_WITH_EGRESS,
            'isolated': ec2.SubnetType.PRIVATE_ISOLATED
        }
        
        return [ec2.SubnetConfiguration(
            name=name,
            subnet_type=subnet_type_map[subnet_type],
            cidr_mask=cidr_mask
        ) for name in names]

    
    def create_vpc(self ,vpc_config ,identifier ,vpc_name , vpc_cidr, vpc_maz_azs, nat_gw,public_subnet_count, public_subnet_mask,private_subnet_count, private_subnet_mask,isolated_subnet_count, isolated_subnet_mask):

        subnet_configs = []
        for subnet_spec in vpc_config.SUBNETS:
            mask = public_subnet_mask if subnet_spec.subnet_type == "public" else \
                private_subnet_mask if subnet_spec.subnet_type == "private" else isolated_subnet_mask
            subnet_configs.extend(self.create_subnet_configurations(
                subnet_spec.names, subnet_spec.subnet_type, mask))

        self.vpc = ec2.Vpc(
            self, identifier,
            vpc_name=vpc_name,
            ip_addresses=ec2.IpAddresses.cidr(vpc_cidr),
            max_azs= vpc_maz_azs,
            nat_gateways= nat_gw,
            subnet_configuration=subnet_configs
        )
        Tags.of(self.vpc).add("Name", vpc_name)
        
        # Create SSM parameters for VPC ID
        ssm.StringParameter(
            self, f"{identifier}-vpc-id-param",
            parameter_name=f"/{vpc_name}/id",
            string_value=self.vpc.vpc_id,
            description=f"VPC ID for {vpc_name}"
        )
        
        # Create SSM parameters for public subnet IDs
        for i, subnet in enumerate(self.vpc.public_subnets):
            ssm.StringParameter(
                self, f"{identifier}-public-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/public-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Public Subnet {i+1} ID for {vpc_name}"
            )
            ssm.StringParameter(
                self, f"{identifier}-public-subnet-{i+1}-az-param",
                parameter_name=f"/{vpc_name}/public-subnet-{i+1}/az",
                string_value=subnet.availability_zone,
                description=f"Public Subnet {i+1} AZ for {vpc_name}"
            )
        
        # Create SSM parameters for private subnet IDs
        for i, subnet in enumerate(self.vpc.private_subnets):
            ssm.StringParameter(
                self, f"{identifier}-private-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/private-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Private Subnet {i+1} ID for {vpc_name}"
            )
            ssm.StringParameter(
                self, f"{identifier}-private-subnet-{i+1}-az-param",
                parameter_name=f"/{vpc_name}/private-subnet-{i+1}/az",
                string_value=subnet.availability_zone,
                description=f"Private Subnet {i+1} AZ for {vpc_name}"
            )
        
        # Create SSM parameters for isolated subnet IDs
        for i, subnet in enumerate(self.vpc.isolated_subnets):
            ssm.StringParameter(
                self, f"{identifier}-isolated-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/isolated-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Isolated Subnet {i+1} ID for {vpc_name}"
            )            
            
        # Return the VPC
        return self.vpc


