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
    VPC_NAME: str
    ALB_SG_ID: str
    CERTIFICATE_ARN: str
    SG_DESC: str




ALB_EXCHANGE = ALBConfig(
    ALB_NAME=f'{ENV}-{COMMON_NAME}-alb',
    ALB_CFN_ID='alb_cfn_id',
    VPC_NAME=f'{ENV}-{COMMON_NAME}-vpc',
    ALB_SG_ID= None,
    CERTIFICATE_ARN= None,
    SG_DESC='Description'
)

ALB_DEV = ALBConfig(
    ALB_NAME=f'dev-{COMMON_NAME}-alb',
    ALB_CFN_ID='alb_cfn_id',
    VPC_NAME=f'dev-{COMMON_NAME}-vpc',
    ALB_SG_ID= None,
    CERTIFICATE_ARN= None,
    SG_DESC='Description'
)

ALB_LIST = [ALB_EXCHANGE,ALB_DEV]