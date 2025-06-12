# config.py
from dataclasses import dataclass, field
import uuid
from typing import List

from aws_cdk import (
    aws_ec2 as ec2,
    aws_elasticloadbalancingv2 as elbv2,
)

# Generate a unique suffix for resource names to avoid conflicts
unique_suffix = str(uuid.uuid4())[:8].lower()

@dataclass
class VpcConfig:
    """Configuration for the VPC."""
    VPC_CFN_ID: str = f"VPC-{unique_suffix}"
    VPC_NAME: str = f"my-application-vpc-{unique_suffix}"
    MAX_AZS: int = 2 # Number of Availability Zones to use

@dataclass
class Ec2InstanceConfig:
    """Configuration for each EC2 instance."""
    INSTANCE_CFN_ID: str
    INSTANCE_NAME: str
    INSTANCE_TYPE: ec2.InstanceType
    MACHINE_IMAGE: ec2.IMachineImage
    USER_DATA_SCRIPT: str = "" # Script to run on instance launch
    
@dataclass
class AlbConfig:
    """Configuration for the Application Load Balancer."""
    ALB_CFN_ID: str = f"ALB-{unique_suffix}"
    ALB_NAME: str = f"my-app-alb-{unique_suffix}"
    LISTENER_PORT: int = 80 # Port for the ALB listener (e.g., HTTP)

@dataclass
class InfrastructureConfig:
    """Overall infrastructure configuration."""
    VPC: VpcConfig = field(default_factory=VpcConfig)
    ALB: AlbConfig = field(default_factory=AlbConfig)
    EC2_INSTANCES: List[Ec2InstanceConfig] = field(default_factory=list)

# --- Define Your Infrastructure Configuration Here ---

# Example: Two EC2 instances with a basic Nginx user data script
nginx_user_data = """#!/bin/bash
yum update -y
yum install -y nginx
systemctl start nginx
systemctl enable nginx
echo "Hello from EC2 instance on $(hostname -f)!" > /usr/share/nginx/html/index.html
"""

AppInfrastructureConfig = InfrastructureConfig(
    VPC=VpcConfig(
        MAX_AZS=2 # You can change this to 1, 2, or 3
    ),
    ALB=AlbConfig(
        LISTENER_PORT=80 # Change to 443 for HTTPS, remember to add certificates
    ),
    EC2_INSTANCES=[
        Ec2InstanceConfig(
            INSTANCE_CFN_ID=f"EC2Instance1-{unique_suffix}",
            INSTANCE_NAME=f"WebAppInstance1-{unique_suffix}",
            INSTANCE_TYPE=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
            MACHINE_IMAGE=ec2.MachineImage.latest_amazon_linux(), # Use Amazon Linux 2
            USER_DATA_SCRIPT=nginx_user_data
        ),
        Ec2InstanceConfig(
            INSTANCE_CFN_ID=f"EC2Instance2-{unique_suffix}",
            INSTANCE_NAME=f"WebAppInstance2-{unique_suffix}",
            INSTANCE_TYPE=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
            MACHINE_IMAGE=ec2.MachineImage.latest_amazon_linux(), # Use Amazon Linux 2
            USER_DATA_SCRIPT=nginx_user_data
        ),
        # Add more Ec2InstanceConfig objects here to create more instances
        # Ec2InstanceConfig(
        #     INSTANCE_CFN_ID=f"EC2Instance3-{unique_suffix}",
        #     INSTANCE_NAME=f"WebAppInstance3-{unique_suffix}",
        #     INSTANCE_TYPE=ec2.InstanceType.of(ec2.InstanceClass.T2, ec2.InstanceSize.MICRO),
        #     MACHINE_IMAGE=ec2.MachineImage.latest_amazon_linux(),
        #     USER_DATA_SCRIPT=nginx_user_data
        # ),
    ]
)
