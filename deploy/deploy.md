# Deployment

**Time to deploy**: Approximately 60 minutes

The steps will be done in TRE project account where the Amazon Machine Images need to be created.
You can choose to do this in centralised account if using the centralised AMI management
capability of SWB.

## Log in to the EC2 instance

- [ ] Logon to AWS the management console for TRE project account.
- [ ] Follow these [instructions](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/session-manager.html)
  to learn how to
  connect via SSM to the EC2 instance created in Step 1A.
- [ ] Run the following command to initialise your environment:

    ```shell
    sudo -iu ec2-user
    ```

## Download repo

- [ ] Download the source code repo using below command. You would need to provide your
      git credentials if required.

    ```console
    git clone https://github.com/HicResearch/treehoose-ec2-builder.git /home/ec2-user/tmp/tre/src
    ```

## Bootstrap CDK app

- [ ] Run below commands to create and activate virtual environment for the CDK application.

    ```console
    cd /home/ec2-user/tmp/tre/src/treehoose-ec2-builder
    python3 -m venv .venv
    source .venv/bin/activate
    ```

- [ ] Install the dependencies

    ```console
    pip install -r requirements.txt
    ```

- [ ] Bootstrap the CDK app

    Ensure that you have the correct AWS CLI credentials configured for the account
    in which you want to deploy the stacks.
    Alternatively pass the correct profile using `--profile PROFILE_NAME` in all cdk commands

    ```console
    alias cdk="npx aws-cdk@2.x"
    cdk bootstrap aws://ACCOUNT-NUMBER/REGION
    ```

> Region will be the region in which you want to deploy the infrastructure

## Update configuration for CDK app

- [ ] Update below parameters in `cdk.json` file.

    **al2_config>base_image_id** :  On the deployment instance run below command to get
    the AMI id and use the appropriate LTS AMI id

    ```aws ec2 describe-images --filters "Name=name,Values=amzn2*MATE*" --query "Images[*].[ImageId,Name,Description]"```

    **ubuntu_config>base_image_id** :  On the deployment instance run below command to get
    the AMI id and use the appropriate LTS AMI id

    ```aws ec2 describe-images --filters "Name=name,Values=ubuntu*server*" --query "Images[*].[ImageId,Name,Description]"```

    **vpc_id** : The id of the vpc created by deployment
    instance template. Use this from the CloudFormation output of
    stack `TREDeploymentInstance`

    **subnet_id** : The id of the subnet created by deployment
    instance template. Use this from the CloudFormation output of
    stack `TREDeploymentInstance`

    Optionally, you can also update the `root_volume_size` and `instance_types`
    parameters for each pipeline based on the requirements.

    Add the required tags inside `resource_tags`.

## Deploy Image Builder Pipelines

- [ ] Deploy `Al2MateImagebuilderPipeline` stack which will deploy
   the image builder pipeline to create an AMI with Amazon Linux 2 with
   MATE UI, xrdp setup, Libreoffice apps and Firefox installed.

   ```console
   cdk deploy --all
   ```

## Run the image builder pipeline

You can automate the image builder pipeline by updating
the code in cdk application.
Currently once the pipeline is created you will need to run
the image builder pipeline manually.

Follow [these](https://docs.aws.amazon.com/imagebuilder/latest/userguide/pipelines-run.html)
instructions to run image builder pipeline.

Once the image builder pipeline is completed an AMI will be available for use.
If the image builder pipeline runs into error, logs are available in CloudWatch.

## Add new products to service workbench

Cloudformation templates to add the new workspace types
as products in Service workbench are available in
[Service Catalog Products](../service-catalog-products/) folder.

```console
# copy templates
cp /home/ec2-user/tmp/tre/src/treehoose-ec2-builder/service-catalog-products/*.yml /home/ec2-user/tmp/service-workbench-on-aws-5.2.7/addons/addon-base-raas/packages/base-raas-cfn-templates/src/templates/service-catalog

# change permissions
chmod 664 /home/ec2-user/tmp/service-workbench-on-aws-5.2.7/addons/addon-base-raas/packages/base-raas-cfn-templates/src/templates/service-catalog/*
```

Follow [these](https://github.com/awslabs/service-workbench-on-aws/tree/mainline#adding-a-custom-service-catalog-product)
instructions to add the workspace types
as custom products.

Example config

```console
  {
    filename: 'al2-mate',
    displayName: 'Amazon Linux 2 Desktop',
    description: `* An Amazon Linux 2 Desktop instance with MATE gui and RDP access`,
  },
  {
    filename: 'ubuntu-mate',
    displayName: 'Ubuntu Desktop',
    description: `* An Ubuntu Desktop instance with MATE gui and RDP access`,
  }
```

## Redeploy service workbench

Run below command to re-deploy service workbench

  ```bash
  cd /home/ec2-user/tmp/service-workbench-on-aws-5.2.7
  ./scripts/environment-deploy.sh treprod
  ```
