# Operations

## Adding Image Builder component

EC2 Image Builder uses a component management application AWS Task Orchestrator and Executor (AWSTOE) that
helps you orchestrate complex workflows,
modify system configurations, and test your systems with YAML-based script components.

[Components](../src/components/) folder contains the YAML-based configuration
files that can be used in image recipes.

Each image pipeline has a bespoke managed policy asssociated with the IAM role
associated to the instance role. Add the necessary additonal permissions as required.

The security group associated with the ec2 instance created by image builder
only allows outbound HTTP and HTTPS traffic to IPV4 addresses. Update
the security group as required for the image builder pipeline.

Redeploy the cdk stacks for image builder pipeline that use
the updated component. This will automatically trigger deployment
of `S3Ops` stack.

## Updating Image Builder component

When an existing component is updated, manually update the
version number of the component in the cdk stacks else the
deployment will fail.

Redeploy the cdk stacks for image builder pipeline that use
the updated component. This will automatically trigger deployment
of `S3Ops` stack.
