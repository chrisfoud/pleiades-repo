#!/usr/bin/env python3

import aws_cdk as cdk
import os

# from network_compute.stack import UnitTestStack
# from database_infra.database_stack import Database
from s3_bucket.s3_bucket import s3bucket
from compute_infra.compute_infra import EC2ALBStack

app = cdk.App()
# UnitTestStack(app, "UnitTestStack",
#                  env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"],region=os.environ["CDK_DEFAULT_REGION"])
#                                      )

# Database(app, "Database",
#                  env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"],region=os.environ["CDK_DEFAULT_REGION"])
#                                      )

s3bucket(app, "s3bucket",
                 env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])
                                     )

EC2ALBStack(app, "EC2ALBStack",
                 env=cdk.Environment(account=os.environ["CDK_DEFAULT_ACCOUNT"], region=os.environ["CDK_DEFAULT_REGION"])
                                     )

app.synth()