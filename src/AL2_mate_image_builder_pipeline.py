from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_imagebuilder as imagebuilder
from aws_cdk import aws_ssm as ssm
from cdk_nag import NagSuppressions
from constructs import Construct


class Al2MateImagebuilderPipeline(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        al2_config = self.node.try_get_context("al2_config")

        bucket_name = ssm.StringParameter.from_string_parameter_name(
            self,
            "rComponentsBucketName",
            "/centralised-amis/components-bucket-name",
        ).string_value

        vpc_id = self.node.try_get_context("vpc_id")

        vpc = ec2.Vpc.from_lookup(self, "rVpc", vpc_id=vpc_id)

        # NOTE: when creating components, version number is supplied manually. If you update the components yaml and
        # need a new version deployed, version need to be updated manually.
        bucket_uri = "s3://" + bucket_name + "/components/amazon_linux"

        component_firefox_uri = bucket_uri + "/install_firefox.yml"
        component_firefox = imagebuilder.CfnComponent(
            self,
            "rComponentFirefox",
            name="InstallFirefox",
            platform="Linux",
            version="1.0.0",
            uri=component_firefox_uri,
        )

        component_libreoffice_uri = bucket_uri + "/install_libreoffice.yml"
        component_libreoffice = imagebuilder.CfnComponent(
            self,
            "rComponentLibreoffice",
            name="InstallLibreoffice",
            platform="Linux",
            version="1.0.0",
            uri=component_libreoffice_uri,
        )

        enable_xrdp_uri = bucket_uri + "/enable_xrdp.yml"
        component_xrdp = imagebuilder.CfnComponent(
            self,
            "rComponentXrdp",
            name="EnableXrdp",
            platform="Linux",
            version="1.0.0",
            uri=enable_xrdp_uri,
        )

        # recipe that installs all of above components together with a Amazon Linux 2 with MATE base image
        recipe = imagebuilder.CfnImageRecipe(
            self,
            "AmazonLinuxMateWorkspaceRecipe",
            name="rAmazonLinuxMateWorkspaceRecipe",
            version="1.0.0",
            components=[
                {"componentArn": component_firefox.attr_arn},
                {"componentArn": component_libreoffice.attr_arn},
                {"componentArn": component_xrdp.attr_arn},
            ],
            parent_image=al2_config.get("base_image_id"),
            block_device_mappings=[
                imagebuilder.CfnImageRecipe.InstanceBlockDeviceMappingProperty(
                    device_name="/dev/xvda",
                    ebs=imagebuilder.CfnImageRecipe.EbsInstanceBlockDeviceSpecificationProperty(
                        volume_size=al2_config.get("root_volume_size"),
                        volume_type="gp3",
                    ),
                )
            ],
        )

        custom_managed_policy = iam.ManagedPolicy(
            self,
            "rAl2WorkspaceManagedPolicy",
            statements=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ssm:DescribeAssociation",
                        "ssm:GetDeployablePatchSnapshotForInstance",
                        "ssm:GetDocument",
                        "ssm:DescribeDocument",
                        "ssm:GetManifest",
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                        "ssm:ListAssociations",
                        "ssm:ListInstanceAssociations",
                        "ssm:PutInventory",
                        "ssm:PutComplianceItems",
                        "ssm:PutConfigurePackageResult",
                        "ssm:UpdateAssociationStatus",
                        "ssm:UpdateInstanceAssociationStatus",
                        "ssm:UpdateInstanceInformation",
                    ],
                    resources=[
                        "*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ssmmessages:CreateControlChannel",
                        "ssmmessages:CreateDataChannel",
                        "ssmmessages:OpenControlChannel",
                        "ssmmessages:OpenDataChannel",
                    ],
                    resources=[
                        "*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "ec2messages:AcknowledgeMessage",
                        "ec2messages:DeleteMessage",
                        "ec2messages:FailMessage",
                        "ec2messages:GetEndpoint",
                        "ec2messages:GetMessages",
                        "ec2messages:SendReply",
                    ],
                    resources=[
                        "*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "imagebuilder:GetComponent",
                    ],
                    resources=[
                        "*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "kms:Decrypt",
                    ],
                    resources=[
                        "*",
                    ],
                    conditions={
                        "ForAnyValue:StringEquals": {
                            "kms:EncryptionContextKeys": "aws:imagebuilder:arn",
                            "aws:CalledVia": ["imagebuilder.amazonaws.com"],
                        }
                    },
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "s3:GetObject",
                    ],
                    resources=[
                        "arn:aws:s3:::ec2imagebuilder*",
                    ],
                ),
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=[
                        "logs:CreateLogStream",
                        "logs:CreateLogGroup",
                        "logs:PutLogEvents",
                    ],
                    resources=["arn:aws:logs:*:*:log-group:/aws/imagebuilder/*"],
                ),
            ],
        )

        # below role is assumed by ec2 instance
        role = iam.Role(
            self,
            "rAmazonLinuxMateWorkspaceInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        )

        role.add_managed_policy(custom_managed_policy)

        # create an instance profile to attach the role
        instance_profile = iam.CfnInstanceProfile(
            self, "rAmazonLinuxMateWorkspaceInstanceProfile", roles=[role.role_name]
        )

        security_group = ec2.SecurityGroup(
            self,
            "rSecurityGroup",
            vpc=vpc,
            allow_all_outbound=False,
            description="Security group for Amazon Linux 2 Mate custom image",
        )

        security_group.add_egress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"), ec2.Port.tcp(80), "Allow http traffic"
        )
        security_group.add_egress_rule(
            ec2.Peer.ipv4("0.0.0.0/0"), ec2.Port.tcp(443), "Allow https traffic"
        )

        # create infrastructure configuration to supply instance type
        infra_config = imagebuilder.CfnInfrastructureConfiguration(
            self,
            "rAmazonLinuxMateWorkspaceInfraConfig",
            name="rAmazonLinuxMateInfraConfig",
            instance_types=al2_config.get("instance_types"),
            instance_profile_name=instance_profile.ref,
            subnet_id=self.node.try_get_context("subnet_id"),
            security_group_ids=[security_group.security_group_id],
        )

        # infrastructure need to wait for instance profile to complete before beginning deployment.
        infra_config.add_dependency(instance_profile)

        # build the imagebuilder pipeline
        pipeline = imagebuilder.CfnImagePipeline(
            self,
            "rAmazonLinuxMateWorkspacePipeline",
            name="AmazonLinuxMateWorkspaceImagePipeline",
            image_recipe_arn=recipe.attr_arn,
            infrastructure_configuration_arn=infra_config.attr_arn,
        )

        pipeline.add_dependency(infra_config)

        NagSuppressions.add_resource_suppressions(
            custom_managed_policy,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "Permissions copied from AWS managed policies AmazonSSMManagedInstanceCore and EC2InstanceProfileForImageBuilder",
                },
            ],
            apply_to_children=True,
        )
