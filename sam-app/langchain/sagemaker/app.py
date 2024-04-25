import json
import os
import boto3
from langchain.llms.sagemaker_endpoint import SagemakerEndpoint, LLMContentHandler
from langchain.chains.conversation.prompt import PROMPT
from typing import Dict
from chat import chat

# environment variables
session_table_name = os.environ["SessionTableName"]
endpoint_name = os.environ["EndpointName"]


class ContentHandler(LLMContentHandler):
    content_type = "application/json"
    accepts = "application/json"

    def transform_input(self, prompt: str, model_kwargs: Dict) -> bytes:
        input_str = json.dumps(
            {"inputs": prompt, "parameters": model_kwargs},
            ensure_ascii=False,
        )
        return input_str.encode("utf-8")

    def transform_output(self, output: bytes) -> str:
        response_json = json.loads(output.read().decode("utf-8"))
        return response_json[0]["generated_text"]


# init dependencies outside of handler
boto3_session = boto3.session.Session()
sagemaker = boto3_session.client("sagemaker-runtime")
llm = SagemakerEndpoint(
    endpoint_name=endpoint_name,
    client=sagemaker,
    model_kwargs={"temperature": 0.5},
    content_handler=ContentHandler(),
    streaming=True,
)
ai_prefix = "AI"  # use default
prompt = PROMPT  # use default


def handler(event, context):
    # call the common chat function in the layer/langchain_common/chat.py
    chat(event, llm, boto3_session, session_table_name, ai_prefix, prompt)
    return {"statusCode": 200}
