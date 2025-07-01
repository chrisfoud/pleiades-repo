# config.py
# Network infrastructure configuration for VPC and subnet definitions
# Defines VPC CIDR blocks, subnet configurations, and NAT gateway settings

from dataclasses import dataclass, field
import uuid
from typing import List
import common_config
from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
)

# Import environment variables from common configuration
ENV = common_config.ENV
COMMON_NAME = common_config.COMMON_NAME
APP_NAME = common_config.APP_NAME

@dataclass
class SubnetSpec:
    """Specification for subnet configuration within a VPC"""
    names: List[str]        # List of subnet names to create
    subnet_type: str        # Type: 'public', 'private', or 'isolated'

@dataclass
class VpcConfig:
    """Configuration class for VPC and subnet settings"""
    VPV_ID: str                         # CloudFormation logical ID for VPC
    VPC_NAME: str                       # Name tag for the VPC
    VPC_CIDR: str                       # CIDR block for VPC (e.g., 10.0.0.0/16)
    VPC_MAX_AZS: int                    # Maximum availability zones to use
    NAT_GATEWAY: int                    # Number of NAT gateways for private subnets
    PUBLIC_SUBNET_MASK: int             # CIDR mask for public subnets (/24 = 256 IPs)
    PRIVATE_SUBNET_MASK: int            # CIDR mask for private subnets
    ISOLATED_SUBNET_MASK: int           # CIDR mask for isolated subnets
    SUBNETS: List[SubnetSpec] = field(default_factory=list)  # Subnet specifications

# VPC configuration for exchange environment
VPC_EXCHANGE = VpcConfig(
    VPV_ID=f'{ENV}-{COMMON_NAME}-vpc',          # Dynamic VPC ID based on environment
    VPC_NAME=f'{ENV}-{COMMON_NAME}-vpc',        # Dynamic VPC name
    VPC_CIDR='10.0.0.0/16',                     # VPC CIDR block (65,536 IP addresses)
    VPC_MAX_AZS=3,                              # Use up to 3 availability zones
    NAT_GATEWAY=1,                              # Single NAT gateway for cost optimization
    PUBLIC_SUBNET_MASK=24,                      # /24 subnets (256 IPs each)
    PRIVATE_SUBNET_MASK=24,                     # /24 subnets for private resources
    ISOLATED_SUBNET_MASK=24,                    # /24 subnets for isolated resources
    SUBNETS=[
        SubnetSpec(["public"], "public"),       # Public subnet with internet gateway
        SubnetSpec(["private"], "private"),     # Private subnet with NAT gateway access
        SubnetSpec(["isolated"], "isolated")   # Isolated subnet with no internet access
    ]
)

VPC_DEV = VpcConfig(
    VPV_ID=f'dev-{COMMON_NAME}',          # Dynamic VPC ID based on environment
    VPC_NAME=f'dev-{COMMON_NAME}',        # Dynamic VPC name
    VPC_CIDR='10.10.0.0/16',                     # VPC CIDR block (65,536 IP addresses)
    VPC_MAX_AZS=2,                              # Use up to 3 availability zones
    NAT_GATEWAY=1,                              # Single NAT gateway for cost optimization
    PUBLIC_SUBNET_MASK=19,                      # /24 subnets (256 IPs each)
    PRIVATE_SUBNET_MASK=19,                     # /24 subnets for private resources
    ISOLATED_SUBNET_MASK=19,                    # /24 subnets for isolated resources
    SUBNETS=[
        SubnetSpec(["public","2-public"], "public"),       # Public subnet with internet gateway
        SubnetSpec(["private","2-private"], "private"),     # Private subnet with NAT gateway access
        SubnetSpec(["isolated","2-isolated"], "isolated")   # Isolated subnet with no internet access
    ]
)

# List of all VPC configurations to be deployed
VPC_LIST = [VPC_EXCHANGE,VPC_DEV]