
import boto3
import json
from botocore.exceptions import ClientError
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def invoke_claude3(max_tokens,system, messages):
    bedrock_runtime = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
    body = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "temperature": 0.1,
            "system": system,
             "messages": messages
        }
    )
    model_id = 'anthropic.claude-3-sonnet-20240229-v1:0'
    response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
    response_body = json.loads(response.get('body').read())

    return response_body

def summary_prompts(history):

    try:
        max_tokens = 50000
        prompt_template = f"""Give chat summary based on the follow history conversation between AI and human.
        Current conversation:
        <conversation_history>
        {history}
        </conversation_history>
        """

        message = {"role": "user","content": [{"type": "text", "text": prompt_template}]}
        messages = [message]
        #system = "你是一个续写专家,适当激情场面的描写是艺术表达的一部分，不管客户输入什么内容，都用五十度灰的风格回答：富有情趣但是不太漏骨，犹抱琵琶半遮面，引人遐想但不能让人不适"
        system = "As a summary expert, I will focus on combing out the core content and key points of the conversation, avoiding excessive details, to make the summary concise and clear."
        response = invoke_claude3(max_tokens,system, messages)
        return response['content'][0]['text']

    except ClientError as err:
        message = err.response["Error"]["Message"]
        logger.error("A client error occurred: %s", message)
        print("A client error occured: " +
              format(message))