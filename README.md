# AMI builder

This add-on will enable creation of be-spoke AMIs based on research needs.
It provides a standardised way of building AMIs using EC2 image builder with a
plug and play component setup to enable deployment on different tools based on
specific needs.

Currently available AMIs through this add-on are :

- Amazon Linux 2 server with MATE gui with Firefox and Libreoffice installed. Allows RDP connections in addition to SSH.
- Ubuntu server with MATE gui with deafult tools. Allows RDP connections in addition to SSH.

This add-on is extensible and easily customisable to enable users to
package supported softwares in existing image types
or create new pipelines from scratch.

## Pre-requisites

SWB on AWS does not allow RDP sessions for Linux based workspaces by default.
Deploy [this](https://github.com/HicResearch/treehoose-swb-customisations) add-on
before providing Linux based workspaces to researchers.

## Considerations

The image builder pipelines do not have test steps currently.
Its recommended that the user adds them based on the softwares they install.

The user is advised to patch the softwares on the AMIs regularly and have
a strategy for the TRE users to use latest patched AMIs.

## Security

When creating new workspace product templates to be used in Service Catalog,
ensure that the IAM permissions boundary for the IAM instance role has the following
Deny policy. This is to ensure that the IAM credentials issued to the workspace cannot
be used outside the context of the workspace.

```yaml
    - Effect: Deny
    Action: '*'
    Resource: '*'
    Condition:
        StringNotEquals:
        "aws:Ec2InstanceSourceVPC": "${aws:SourceVpc}"
        "aws:ec2InstanceSourcePrivateIPv4": "${aws:VpcSourceIp}"
        BoolIfExists:
        "aws:ViaAWSService": "false"
        "Null":
        "aws:ec2InstanceSourceVPC": "false"
```

## Deployment Instructions

---
Follow these [instructions](./deploy/deploy.md) to deploy Image Builder pipelines.

## Operational Instructions

---
Follow these [instructions](./operations/operations.md) to operate Image Builder pipelines.
