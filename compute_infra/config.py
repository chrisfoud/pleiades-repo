# config.py
# Configuration file for AWS compute infrastructure resources
# Defines ALB and EC2 configurations for different environments

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
class ALBConfig:
    """Configuration class for Application Load Balancer (ALB) settings"""
    ALB_NAME: str           # Name of the ALB resource
    ALB_CFN_ID: str         # CloudFormation ID for the ALB
    ALB_VPC: str            # VPC where ALB will be deployed
    ALB_SG_ID: str          # Security Group ID for ALB (None for auto-creation)
    CERTIFICATE_ARN: str    # SSL certificate ARN for HTTPS listeners
    SG_DESC: str            # Description for the security group

@dataclass
class EC2Config:
    """Configuration class for EC2 instance settings"""
    EC2_NAME: str               # Name of the EC2 instance
    EC2_VPC: str                # VPC where EC2 will be deployed
    EC2_INSTANCE_TYPE: str      # Instance type (e.g., t3.micro, t3.small)
    EC2_SG_ID: str              # Security Group ID (None for auto-creation)
    INSTANCE_IDS: List[str]     # List to store created instance IDs
    AMI_REGION: str             # AWS region for AMI lookup
    EC2_SUBNET_NAME: str        # Subnet name to lookup (None for random selection)
    EC2_AZ: str                 # Availability zone for instance placement
    AMI_ID: str                 # Amazon Machine Image ID
    EC2_ALB: str                # Associated ALB name (None if no ALB)
    EC2_KEYPAIR: str            # SSH keypair name (None if no SSH access)



# Application Load Balancer configuration for exchange environment
ALB_EXCHANGE = ALBConfig(
    ALB_NAME=f'{ENV}-{COMMON_NAME}-alb',        # Dynamic ALB name based on environment
    ALB_CFN_ID='alb_cfn_id',                    # CloudFormation logical ID
    ALB_VPC=f'{ENV}-{COMMON_NAME}-vpc',         # Target VPC for ALB deployment
    ALB_SG_ID=None,                             # Auto-create security group
    CERTIFICATE_ARN=None,                       # No SSL certificate configured
    SG_DESC='Description'                       # Security group description
)

# ALB_DEV = ALBConfig(
#     ALB_NAME=f'dev-{COMMON_NAME}-alb',
#     ALB_CFN_ID='alb_cfn_id',
#     VPC_NAME=f'dev-{COMMON_NAME}-vpc',
#     ALB_SG_ID= None,
#     CERTIFICATE_ARN= None,
#     SG_DESC='Description'
# )


# EC2_EXCHANGE_1 = EC2Config(
#     EC2_NAME=f'{ENV}-{COMMON_NAME}-ec2',        # Dynamic instance name
#     EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',         # Target VPC the instance will be deployed
#     EC2_INSTANCE_TYPE='t3.micro',               # Define Instance type
#     EC2_SG_ID=None,                             # Enter existing name ID , if None Auto-Create SG
#     AMI_REGION='eu-central-1',                  # Define Region of the AMI
#     EC2_SUBNET_NAME='private',                  # Define the Subnet name as Defined in Network config
#     EC2_AZ='eu-central-1a',                     # Define Availability zone the EC2 will be deployed
#     AMI_ID='ami-016c25765a1fa5a76',             # Windows AMI
#     INSTANCE_IDS=[],                            # Will be populated after creation
#     EC2_ALB=f'{ENV}-{COMMON_NAME}-alb',         # Associate with ALB for load balancing, if None EC2 will not be under ALB
#     EC2_KEYPAIR='test-keypair'                  # Define existing Keypair name, if None EC2 will not have Keypair
# )

# First EC2 instance configuration for exchange application
EC2_EXCHANGE_1 = EC2Config(
    EC2_NAME=f'{ENV}-{COMMON_NAME}-ec2',        # Dynamic instance name
    EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',         # Target VPC
    EC2_INSTANCE_TYPE='t3.micro',               # Small instance for cost optimization
    EC2_SG_ID=None,                             # Auto-create security group
    AMI_REGION='eu-central-1',                  # Frankfurt region
    EC2_SUBNET_NAME='private',                  # Private subnet for application tier
    EC2_AZ='eu-central-1a',                     # Availability zone A
    AMI_ID='ami-016c25765a1fa5a76',             # Amazon Linux 2 AMI
    INSTANCE_IDS=[],                            # Will be populated after creation
    EC2_ALB=f'{ENV}-{COMMON_NAME}-alb',         # Associate with ALB for load balancing
    EC2_KEYPAIR='test-keypair'                  # SSH key for instance access
)

# Second EC2 instance configuration for exchange application (high availability)
EC2_EXCHANGE_2 = EC2Config(
    EC2_NAME=f'{ENV}-{COMMON_NAME}-ec2-2',      # Second instance for redundancy
    EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',         # Same VPC as first instance
    EC2_INSTANCE_TYPE='t3.micro',               # Matching instance type
    EC2_SG_ID=None,                             # Auto-create security group
    AMI_REGION='eu-central-1',                  # Same region
    EC2_SUBNET_NAME='private',                  # Same private subnet
    EC2_AZ='eu-central-1b',                     # Different AZ for high availability
    AMI_ID='ami-016c25765a1fa5a76',             # Same AMI as first instance
    INSTANCE_IDS=[],                            # Will be populated after creation
    EC2_ALB=f'{ENV}-{COMMON_NAME}-alb',         # Same ALB for load distribution
    EC2_KEYPAIR='test-keypair'                  # Define existing Keypair
)

# Domain Controller server configuration (standalone instance)
DC_SERVER_1 = EC2Config(
    EC2_NAME='DC-server-ec2',                   # Fixed name for DC server
    EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',         # Same VPC as other resources
    EC2_INSTANCE_TYPE='t3.micro',               # Small instance for DC services
    EC2_SG_ID=None,                             # Auto-create security group
    AMI_REGION='eu-central-1',                  # Same region
    EC2_SUBNET_NAME='public',                   # Public subnet for external access
    EC2_AZ='eu-central-1c',                     # Third availability zone
    AMI_ID='ami-016c25765a1fa5a76',             # Same base AMI
    INSTANCE_IDS=[],                            # Will be populated after creation
    EC2_ALB=None,                               # No load balancer (standalone service)
    EC2_KEYPAIR='test-keypair'                  # Define existing Keypair
)


# Configuration lists for infrastructure deployment
# List of all ALB configurations to be created
ALB_LIST = [ALB_EXCHANGE]

# List of all EC2 configurations to be created
# Includes exchange application instances and domain controller
EC2_LIST = [EC2_EXCHANGE_1, EC2_EXCHANGE_2, DC_SERVER_1]