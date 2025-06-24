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
    custom_subnets: List[dict] = field(default_factory=list)

VPC_EXCHANGE = VpcConfig(
    VPV_ID=f'{ENV}-{COMMON_NAME}-vpc',
    VPC_NAME=f'{ENV}-{COMMON_NAME}-vpc',
    VPC_CIDR='10.0.0.0/16',
    VPC_MAX_AZS=3,
    NAT_GATEWAY=1,
    PUBLIC_SUBNET_MASK=24,
    PRIVATE_SUBNET_MASK=24,
    ISOLATED_SUBNET_MASK=24,
    custom_subnets=[
        {
            'name': f'{VpcConfig.VPC_NAME}-public-subnet-1',
            'cidr': '10.0.101.0/24',
            'az': 'eu-central-1a',
            'type': 'public'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-private-subnet-1', 
            'cidr': '10.0.102.0/24',
            'az': 'eu-central-1a',
            'type': 'private'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-isolated-subnet-1',
            'cidr': '10.0.103.0/24', 
            'az': 'eu-central-1a',
            'type': 'isolated'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-public-subnet-2',
            'cidr': '10.0.104.0/24',
            'az': 'eu-central-1b',
            'type': 'public'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-private-subnet-2', 
            'cidr': '10.0.105.0/24',
            'az': 'eu-central-1b',
            'type': 'private'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-isolated-subnet-2',
            'cidr': '10.0.106.0/24', 
            'az': 'eu-central-1b',
            'type': 'isolated'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-public-subnet-3',
            'cidr': '10.0.107.0/24',
            'az': 'eu-central-1c',
            'type': 'public'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-private-subnet-3', 
            'cidr': '10.0.108.0/24',
            'az': 'eu-central-1c',
            'type': 'private'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-isolated-subnet-3',
            'cidr': '10.0.109.0/24', 
            'az': 'eu-central-1c',
            'type': 'isolated'
        },
        {
            'name': f'{VpcConfig.VPC_NAME}-public-subnet-1-2',
            'cidr': '10.0.110.0/24', 
            'az': 'eu-central-1c',
            'type': 'isolated'
        }
    ]
)




# VPC_DEV = VpcConfig(
#     VPV_ID=f'dev-{COMMON_NAME}-vpc',
#     VPC_NAME=f'dev-{COMMON_NAME}-vpc',
#     VPC_CIDR='10.10.0.0/16',
#     VPC_MAX_AZS=3,
#     NAT_GATEWAY=1,
#     PUBLIC_SUBNET_MASK=24,
#     PRIVATE_SUBNET_MASK=24,
#     ISOLATED_SUBNET_MASK=24,
#     custom_subnets=[
#     {
#         'name': 'web-subnet-1',
#         'cidr': '10.0.1.0/24',
#         'az': 'eu-central-1a',
#         'type': 'public'
#     },
#     {
#         'name': 'app-subnet-1', 
#         'cidr': '10.0.2.0/24',
#         'az': 'eu-central-1a',
#         'type': 'private'
#     },
#     {
#         'name': 'db-subnet-1',
#         'cidr': '10.0.3.0/24', 
#         'az': 'eu-central-1a',
#         'type': 'isolated'
#     }
#     {
#         'name': 'web-subnet-1',
#         'cidr': '10.0.4.0/24',
#         'az': 'eu-central-1b',
#         'type': 'public'
#     },
#     {
#         'name': 'app-subnet-1', 
#         'cidr': '10.0.5.0/24',
#         'az': 'eu-central-1b',
#         'type': 'private'
#     },
#     {
#         'name': 'db-subnet-1',
#         'cidr': '10.0.6.0/24', 
#         'az': 'eu-central-1b',
#         'type': 'isolated'
#     }{
#         'name': 'web-subnet-1',
#         'cidr': '10.0.7.0/24',
#         'az': 'eu-central-1c',
#         'type': 'public'
#     },
#     {
#         'name': 'app-subnet-1', 
#         'cidr': '10.0.8.0/24',
#         'az': 'eu-central-1c',
#         'type': 'private'
#     },
#     {
#         'name': 'db-subnet-1',
#         'cidr': '10.0.9.0/24', 
#         'az': 'eu-central-1c',
#         'type': 'isolated'
#     }
# )

VPC_LIST = [VPC_EXCHANGE]