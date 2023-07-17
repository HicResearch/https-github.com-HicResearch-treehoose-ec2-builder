import os

from aws_cdk import Duration, Stack
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3_deployment
from aws_cdk import aws_ssm as ssm
from cdk_nag import NagSuppressions
from constructs import Construct

dirname = os.path.dirname(__file__)


class S3Ops(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # S3 Bucket for image components
        ops_bucket = s3.Bucket(
            self,
            "rS3ImageBuilderComponents",
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            bucket_name=f"image-builder-components-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            versioned=True,
        )

        # Delete no current version of component file after 30 days
        ops_bucket.add_lifecycle_rule(
            abort_incomplete_multipart_upload_after=Duration.days(1),
            enabled=True,
            noncurrent_version_expiration=Duration.days(30),
        )

        # set component folder as source for deployment
        source_asset = s3_deployment.Source.asset(os.path.join(dirname, "components"))

        # deploy everything under folder to s3 bucket
        s3_deployment.BucketDeployment(
            self,
            "rStackComponentDeployments",
            destination_bucket=ops_bucket,
            sources=[source_asset],
            destination_key_prefix="components",
        )

        ssm.StringParameter(
            self,
            "rComponentsBucketName",
            parameter_name="/centralised-amis/components-bucket-name",
            string_value=ops_bucket.bucket_name,
            description="Bucket name to upload image builder components",
            tier=ssm.ParameterTier.STANDARD,
        )

        NagSuppressions.add_resource_suppressions(
            ops_bucket,
            suppressions=[
                {
                    "id": "AwsSolutions-S1",
                    "reason": "This bucket does not need server access logs",
                }
            ],
        )

        NagSuppressions.add_resource_suppressions_by_path(
            self,
            path="/S3Ops/Custom::CDKBucketDeployment8693BB64968944B69AAFB0CC9EB8756C/ServiceRole",
            suppressions=[
                {
                    "id": "AwsSolutions-IAM4",
                    "reason": "CDK created permissions for custom resource",
                },
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "CDK created permissions for custom resource",
                },
            ],
            apply_to_children=True,
        )
