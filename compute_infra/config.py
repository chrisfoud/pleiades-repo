# config.py
from dataclasses import dataclass, field
import uuid
from typing import List
import common_config
from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
)

ENV = common_config.ENV
COMMON_NAME = common_config.COMMON_NAME
APP_NAME = common_config.APP_NAME

@dataclass
class ALBConfig:
    ALB_NAME: str
    ALB_CFN_ID: str
    ALB_VPC: str
    ALB_SG_ID: str
    CERTIFICATE_ARN: str
    SG_DESC: str

@dataclass
class EC2Config:
    EC2_NAME: str
    EC2_VPC: str
    EC2_INSTANCE_TYPE: str
    EC2_SG_ID: str
    INSTANCE_IDS: List[str]
    AMI_REGION: str
    EC2_SUBNET: str  # Specific subnet number (1-3) or None for random
    AMI_ID: str
    EC2_ALB: str
    EC2_KEYPAIR: str



ALB_EXCHANGE = ALBConfig(
    ALB_NAME=f'{ENV}-{COMMON_NAME}-alb',
    ALB_CFN_ID='alb_cfn_id',
    ALB_VPC=f'{ENV}-{COMMON_NAME}-vpc',
    ALB_SG_ID= None,
    CERTIFICATE_ARN= None,
    SG_DESC='Description'
)

# ALB_DEV = ALBConfig(
#     ALB_NAME=f'dev-{COMMON_NAME}-alb',
#     ALB_CFN_ID='alb_cfn_id',
#     VPC_NAME=f'dev-{COMMON_NAME}-vpc',
#     ALB_SG_ID= None,
#     CERTIFICATE_ARN= None,
#     SG_DESC='Description'
# )

EC2_EXCHANGE_1 = EC2Config(
    EC2_NAME=f'{ENV}-{COMMON_NAME}-ec2',
    EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',
    EC2_INSTANCE_TYPE='t3.micro',
    EC2_SG_ID= None,
    AMI_REGION='eu-central-1',
    EC2_SUBNET='1',  # Specific subnet (1-3) or None for random
    AMI_ID='ami-016c25765a1fa5a76',
    INSTANCE_IDS= [],
    EC2_ALB=f'{ENV}-{COMMON_NAME}-alb',  # Specify ALB name or None
    EC2_KEYPAIR='test-keypair'  # Specify keypair name or None
)

EC2_EXCHANGE_2 = EC2Config(
    EC2_NAME=f'{ENV}-{COMMON_NAME}-ec2-2',
    EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',
    EC2_INSTANCE_TYPE='t3.micro',
    EC2_SG_ID= None,
    AMI_REGION='eu-central-1',
    EC2_SUBNET='2',  # Specific subnet (1-3) or None for random
    AMI_ID='ami-016c25765a1fa5a76',
    INSTANCE_IDS= [],
    EC2_ALB=f'{ENV}-{COMMON_NAME}-alb',  # Specify ALB name or None
    EC2_KEYPAIR='test-keypair'  # Specify keypair name or None
)

DC_SERVER_1 = EC2Config(
    EC2_NAME=f'DC-server-ec2',
    EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',
    EC2_INSTANCE_TYPE='t3.micro',
    EC2_SG_ID= 'sg-041ba334e42258af8',
    AMI_REGION='eu-central-1',
    EC2_SUBNET='3',  # Specific subnet (1-3) or None for random
    AMI_ID='ami-016c25765a1fa5a76',
    INSTANCE_IDS= [],
    EC2_ALB=None,  # Specify ALB name or None
    EC2_KEYPAIR='test-keypair'  # Specify keypair name or None
)

DC_SERVER_2 = EC2Config(
    EC2_NAME=f'DC-server-ec2-2',
    EC2_VPC=f'{ENV}-{COMMON_NAME}-vpc',
    EC2_INSTANCE_TYPE='t3.micro',
    EC2_SG_ID= 'sg-041ba334e42258af8',
    AMI_REGION='eu-central-1',
    EC2_SUBNET=None,  # Specific subnet (1-3) or None for random
    AMI_ID='ami-016c25765a1fa5a76',
    INSTANCE_IDS= [],
    EC2_ALB=None,  # Specify ALB name or None
    EC2_KEYPAIR='test-keypair'  # Specify keypair name or None
)


ALB_LIST = [ALB_EXCHANGE]

EC2_LIST = [EC2_EXCHANGE_1,EC2_EXCHANGE_2,DC_SERVER_1,DC_SERVER_2]