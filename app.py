#!/usr/bin/env python3
import aws_cdk as cdk
import os

from aws_cdk import App, Environment
from network_infra.network_stack import NetworkStack
from compute_infra.compute_infra import ComputeStack

app = App()

NetworkStack(app,"NetworkStack",
               env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])
                )

ComputeStack(app,"ComputeStack",
               env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])
                )

app.synth()
