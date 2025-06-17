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
class VpcConfig:

    VPV_ID: str
    VPC_NAME: str
    VPC_CIDR: str
    VPC_MAX_AZS: int
    NAT_GATEWAY: int
    PUBLIC_SUBNET_MASK: int
    PRIVATE_SUBNET_MASK: int
    ISOLATED_SUBNET_MASK: int

VPC_1 = VpcConfig(
    VPV_ID=f'{ENV}{COMMON_NAME}Vpc',
    VPC_NAME=f'{ENV}-{COMMON_NAME}-vpc',
    VPC_CIDR='10.0.0.0/16',
    VPC_MAX_AZS=3,
    NAT_GATEWAY=1,
    PUBLIC_SUBNET_MASK=24,
    PRIVATE_SUBNET_MASK=24,
    ISOLATED_SUBNET_MASK=24
)

VPC_LIST = [VPC_1]