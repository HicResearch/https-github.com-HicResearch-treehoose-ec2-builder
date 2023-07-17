#!/usr/bin/env python3
import os

from aws_cdk import App, Aspects, Tags
from cdk_nag import AwsSolutionsChecks

from src.AL2_mate_image_builder_pipeline import Al2MateImagebuilderPipeline
from src.s3_ops import S3Ops
from src.Ubuntu_mate_image_builder_pipeline import UbuntuMateImagebuilderPipeline

app = App()
s3_ops_stack = S3Ops(app, "S3Ops")
al2_mate_image_builder_stack = Al2MateImagebuilderPipeline(
    app,
    "Al2MateImagebuilderPipeline",
    env={
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    },
)

ubuntu_mate_image_builder_stack = UbuntuMateImagebuilderPipeline(
    app,
    "UbuntuImagebuilderPipeline",
    env={
        "account": os.environ["CDK_DEFAULT_ACCOUNT"],
        "region": os.environ["CDK_DEFAULT_REGION"],
    },
)

al2_mate_image_builder_stack.add_dependency(s3_ops_stack)
ubuntu_mate_image_builder_stack.add_dependency(s3_ops_stack)

for tag_key, tag_value in app.node.try_get_context("resource_tags").items():
    Tags.of(app).add(tag_key, tag_value)


Aspects.of(app).add(AwsSolutionsChecks())
app.synth()
