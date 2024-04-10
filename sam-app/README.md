# sam-app

This folder contains the AWS [SAM](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) application templates and source code. It is recommended to get yourself familiar with SAM before you start.

## Deployment

### Prerequisites

- Install [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).
- [Configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html#cli-configure-files-methods) with your AWS account credentials.
- Install [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).
- Have docker installed and running. We will use docker to build the Lambda functions.

### Bedrock / LangChainBedrock

Make sure you have the access to the Amazon Bedrock foundation models. You can request the access in the AWS console. Documentation can be found [here](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).

By default these 2 Lambda functions will use Anthropic Claude v2.1 model (`anthropic.claude-v2:1`).

### LangChainSageMaker

This application **_doesn't_** include the deployment of the SageMaker endpoint. You have to have an existing SageMaker endpoint deployed in your AWS account.

Once the SageMaker endpoint is ready, you can set the `EndpointName` environment variable for the Lambda function to use it.

> [!WARNING]
> Not every model on SageMaker support response streaming. If a model doesn't support response streaming, the Lambda function may stuck. You can test the [SageMaker endpoint with LangChain](https://python.langchain.com/docs/integrations/llms/sagemaker) locally to see if it works before you deploy it.

### LangChainOpenAI

Make sure you have an OpenAI API key, or an OpenAI compatible HTTP endpoint.

Once you are ready, configure the `OpenAI_API_Key` or `OpenAI_API_Base` environment variable for the Lambda function to use it.

> [!NOTE]
> Storing credentials in environment variables is not recommended. You can use [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) to store your credentials securely, and use [AWS Parameters and Secrets Lambda Extension](https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_lambda.html) to retrieve them in your Lambda function.

### Deploy

```bash
# Build the Lambda functions, layers, etc.
sam build

# Deploy the whole application
sam deploy --guided
# or use this follow command,modify with your own region and bucket name
# sam deploy --stack-name serverlesschat --region us-east-1  --s3-bucket yourbucketname --capabilities CAPABILITY_NAMED_IAM
```

### Re-Deploy WebSocket API

After you made changes and use `sam deploy` to update the CloudFormation stack, if you modify the template.yaml, you need to `sam build` first.
You may need to re-deploy the WebSocket API manually. You can do this in the AWS console, or use AWS [CLI](https://awscli.amazonaws.com/v2/documentation/api/latest/reference/apigatewayv2/create-deployment.html) / SDK to do it.

If you want to automate this process, you can use [CloudFormation Custom Resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html) to do it.

## Cleanup

```bash
# if you use the default stack name (sam-chat)
sam delete

# if you use a custom stack name
sam delete --stack-name <stack-name>
```
