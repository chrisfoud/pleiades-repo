# Network infrastructure stack for VPC and subnet creation
# Handles VPC deployment with public, private, and isolated subnets
# Stores subnet information in SSM Parameter Store for cross-stack reference

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
import ipaddress

class NetworkStack(Stack):
    """CDK Stack for creating VPC and networking infrastructure"""
    
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self._validated_vpcs = set()
        
        # Create VPCs from configuration list
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
            
            # Export VPC ID for cross-stack reference
            CfnOutput(
                self, f"{vpc_config.VPV_ID}-id-output",
                value=vpc.vpc_id,
                description=f"VPC ID for {vpc_config.VPC_NAME}",
                export_name=f"{vpc_config.VPC_NAME}-id"
            )
    
    def validate_subnet_capacity(self, vpc_cidr: str, vpc_config, public_mask: int, private_mask: int, isolated_mask: int, max_azs: int) -> None:
        """Validate if VPC can accommodate all required subnets collectively"""
        validation_key = f"{vpc_cidr}-{vpc_config.VPC_NAME}"
        if validation_key in self._validated_vpcs:
            return
        
        vpc = ipaddress.IPv4Network(vpc_cidr)
        total_required_addresses = 0
        
        print(f"VPC {vpc_cidr} has {vpc.num_addresses} IP addresses")
        
        for subnet_spec in vpc_config.SUBNETS:
            mask = public_mask if subnet_spec.subnet_type == "public" else \
                private_mask if subnet_spec.subnet_type == "private" else isolated_mask
            subnet_size = 2 ** (32 - mask)
            for name in subnet_spec.names:
                for az in range(1, max_azs + 1):
                    print(f"Subnet {name}-az{az} (/{mask}): {subnet_size} IP addresses")
            total_required_addresses += len(subnet_spec.names) * max_azs * subnet_size
        
        if total_required_addresses > vpc.num_addresses:
            raise ValueError(f"Cannot fit all subnets into {vpc_cidr}. Required: {total_required_addresses}, Available: {vpc.num_addresses}")
        
        self._validated_vpcs.add(validation_key)
    
    def create_subnet_configurations(self, names, subnet_type, cidr_mask) -> List[ec2.SubnetConfiguration]:
        """Create subnet configurations based on type and CIDR mask"""
        # Map string types to CDK subnet types
        subnet_type_map = {
            'public': ec2.SubnetType.PUBLIC,                    # Internet gateway access
            'private': ec2.SubnetType.PRIVATE_WITH_EGRESS,      # NAT gateway for outbound
            'isolated': ec2.SubnetType.PRIVATE_ISOLATED         # No internet access
        }
        
        # Create subnet configuration for each name
        return [ec2.SubnetConfiguration(
            name=name,
            subnet_type=subnet_type_map[subnet_type],
            cidr_mask=cidr_mask
        ) for name in names]

    
    def create_vpc(self, vpc_config, identifier, vpc_name, vpc_cidr, vpc_maz_azs, nat_gw, public_subnet_mask, private_subnet_mask, isolated_subnet_mask):
        """Create VPC with subnets and store references in SSM Parameter Store"""

        # Validate subnet capacity before creating VPC
        self.validate_subnet_capacity(vpc_cidr, vpc_config, public_subnet_mask, private_subnet_mask, isolated_subnet_mask, vpc_maz_azs)

        # Build subnet configurations from VPC config
        subnet_configs = []
        for subnet_spec in vpc_config.SUBNETS:
            # Select appropriate CIDR mask based on subnet type
            mask = public_subnet_mask if subnet_spec.subnet_type == "public" else \
                private_subnet_mask if subnet_spec.subnet_type == "private" else isolated_subnet_mask
            # Add subnet configurations to list
            subnet_configs.extend(self.create_subnet_configurations(
                subnet_spec.names, subnet_spec.subnet_type, mask))

        # Create VPC with specified configuration
        self.vpc = ec2.Vpc(
            self, identifier,
            vpc_name=vpc_name,
            ip_addresses=ec2.IpAddresses.cidr(vpc_cidr),
            max_azs=vpc_maz_azs,                    # Maximum availability zones
            nat_gateways=nat_gw,                    # Number of NAT gateways
            subnet_configuration=subnet_configs      # Subnet layout
        )
        Tags.of(self.vpc).add("Name", f'{vpc_name}-vpc')
        
        # Store VPC ID in SSM Parameter Store for cross-stack reference
        ssm.StringParameter(
            self, f"{identifier}-vpc-id-param",
            parameter_name=f"/{vpc_name}/id",
            string_value=self.vpc.vpc_id,
            description=f"VPC ID for {vpc_name}"
        )
        
        # Store public subnet IDs and availability zones in SSM
        for i, subnet in enumerate(self.vpc.public_subnets):
            # Store subnet ID
            ssm.StringParameter(
                self, f"{identifier}-public-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/public-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Public Subnet {i+1} ID for {vpc_name}"
            )
            # Store availability zone
            ssm.StringParameter(
                self, f"{identifier}-public-subnet-{i+1}-az-param",
                parameter_name=f"/{vpc_name}/public-subnet-{i+1}/az",
                string_value=subnet.availability_zone,
                description=f"Public Subnet {i+1} AZ for {vpc_name}"
            )
        
        # Store private subnet IDs and availability zones in SSM
        for i, subnet in enumerate(self.vpc.private_subnets):
            # Store subnet ID
            ssm.StringParameter(
                self, f"{identifier}-private-subnet-{i+1}-param",
                parameter_name=f"/{vpc_name}/private-subnet-{i+1}/id",
                string_value=subnet.subnet_id,
                description=f"Private Subnet {i+1} ID for {vpc_name}"
            )
            # Store availability zone
            ssm.StringParameter(
                self, f"{identifier}-private-subnet-{i+1}-az-param",
                parameter_name=f"/{vpc_name}/private-subnet-{i+1}/az",
                string_value=subnet.availability_zone,
                description=f"Private Subnet {i+1} AZ for {vpc_name}"
            )
        
        # Create SSM parameters for subnet access by name and AZ based on config
        subnet_type_mapping = {
            'public': self.vpc.public_subnets,
            'private': self.vpc.private_subnets,
            'isolated': self.vpc.isolated_subnets
        }
        
        # Create parameters and tags for each subnet type defined in config
        for subnet_spec in vpc_config.SUBNETS:
            subnet_type = subnet_spec.subnet_type
            subnet_names = subnet_spec.names
            subnets = subnet_type_mapping.get(subnet_type, [])
            
            # Tag each subnet with corresponding name and create parameters
            for subnet_name in subnet_names:
                for i, subnet in enumerate(subnets):
                    # Tag subnet with unique name in format: env-commonname-subnetname-subnet-az
                    az_number = i + 1
                    Tags.of(subnet).add("Name", f"{vpc_name}-{subnet_name}-subnet-{az_number}")
                    # Create SSM parameter
                    ssm.StringParameter(
                        self, f"{identifier}-{subnet_name}-{subnet.availability_zone.replace('-', '')}-param",
                        parameter_name=f"/{vpc_name}/{subnet_name}-subnet/{subnet.availability_zone}/id",
                        string_value=subnet.subnet_id,
                        description=f"{subnet_name} Subnet ID in {subnet.availability_zone} for {vpc_name}"
                    )
        
            
            
        # Return created VPC for further use
        return self.vpc


