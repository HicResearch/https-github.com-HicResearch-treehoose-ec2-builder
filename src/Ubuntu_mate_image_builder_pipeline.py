from aws_cdk import Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_imagebuilder as imagebuilder
from aws_cdk import aws_ssm as ssm
from cdk_nag import NagSuppressions
from constructs import Construct


class UbuntuMateImagebuilderPipeline(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ubuntu_config = self.node.try_get_context("ubuntu_config")

        bucket_name = ssm.StringParameter.from_string_parameter_name(
            self,
            "rComponentsBucketName",
            "/centralised-amis/components-bucket-name",
        ).string_value

        vpc_id = self.node.try_get_context("vpc_id")

        vpc = ec2.Vpc.from_lookup(self, "rVpc", vpc_id=vpc_id)

        # NOTE: when creating components, version number is supplied manually. If you update the components yaml and
        # need a new version deployed, version need to be updated manually.
        bucket_uri = "s3://" + bucket_name + "/components/ubuntu"

        basic_ubuntu_setup_uri = bucket_uri + "/basic_ubuntu_setup.yml"
        basic_ubuntu_setup = imagebuilder.CfnComponent(
            self,
            "rComponentFBasicUbuntuSetup",
            name="BasicUbuntuSetup",
            platform="Linux",
            version="1.0.0",
            uri=basic_ubuntu_setup_uri,
        )

        ubuntu_mate_desktop_uri = bucket_uri + "/install_ubuntu_mate_desktop.yml"
        component_ubuntu_mate_desktop = imagebuilder.CfnComponent(
            self,
            "rComponentMateDesktop",
            name="InstallMateDesktop",
            platform="Linux",
            version="1.0.0",
            uri=ubuntu_mate_desktop_uri,
        )

        install_xrdp_uri = bucket_uri + "/install_xrdp.yml"
        component_xrdp = imagebuilder.CfnComponent(
            self,
            "rComponentXrdp",
            name="InstallXrdp",
            platform="Linux",
            version="1.0.0",
            uri=install_xrdp_uri,
        )

        # recipe that installs all of above components together with a Ubuntu Server with MATE base image
        recipe = imagebuilder.CfnImageRecipe(
            self,
            "UbuntuWorkspaceRecipe",
            name="rUbuntuWorkspaceRecipe",
            version="1.0.0",
            components=[
                {"componentArn": basic_ubuntu_setup.attr_arn},
                {"componentArn": component_ubuntu_mate_desktop.attr_arn},
                {"componentArn": component_xrdp.attr_arn},
            ],
            parent_image=ubuntu_config.get("base_image_id"),
            block_device_mappings=[
                imagebuilder.CfnImageRecipe.InstanceBlockDeviceMappingProperty(
                    device_name="/dev/xvda",
                    ebs=imagebuilder.CfnImageRecipe.EbsInstanceBlockDeviceSpecificationProperty(
                        volume_size=ubuntu_config.get("root_volume_size"),
                        volume_type="gp3",
                    ),
                )
            ],
        )

        custom_managed_policy = iam.ManagedPolicy(
            self,
            "rUbuntuWorkspaceManagedPolicy",
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
            "rUbuntuWorkspaceInstanceRole",
            assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"),
        )

        role.add_managed_policy(custom_managed_policy)

        # create an instance profile to attach the role
        instance_profile = iam.CfnInstanceProfile(
            self, "rUbuntuWorkspaceInstanceProfile", roles=[role.role_name]
        )

        security_group = ec2.SecurityGroup(
            self,
            "rSecurityGroup",
            vpc=vpc,
            allow_all_outbound=False,
            description="Security group for Ubuntu Mate custom image",
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
            "rUbuntuWorkspaceInfraConfig",
            name="rUbuntuInfraConfig",
            instance_types=ubuntu_config.get("instance_types"),
            instance_profile_name=instance_profile.ref,
            subnet_id=self.node.try_get_context("subnet_id"),
            security_group_ids=[security_group.security_group_id],
        )

        # infrastructure need to wait for instance profile to complete before beginning deployment.
        infra_config.add_dependency(instance_profile)

        # build the imagebuilder pipeline
        pipeline = imagebuilder.CfnImagePipeline(
            self,
            "rUbuntuWorkspacePipeline",
            name="UbuntuWorkspaceImagePipeline",
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
