#!/usr/bin/env python3
import aws_cdk as cdk
import os

from aws_cdk import App, Environment
from compute_infra.vpc_alb_ec2_stack import VpcAlbEc2Stack

app = App()

VpcAlbEc2Stack(app,"VpcAlbEc2Stack",
               env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])
                )

app.synth()
