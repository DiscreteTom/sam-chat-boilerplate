import os
import boto3
from langchain.llms.bedrock import Bedrock
from langchain.prompts import PromptTemplate

# environment variables
model_id = os.environ.get("ModelId", "anthropic.claude-v2:1")
session_table_name = os.environ["SessionTableName"]
ai_prefix = os.environ.get(
    "AI_Prefix",
    # by default (Claude), this is "Assistant"
    "Assistant",
)
prompt_template = os.environ.get(
    "PromptTemplate",
    # by default (Claude)
    "\\n{history}\\n\\nHuman: {input}\\n\\nAssistant:\\n",
).replace("\\n", "\n")

# init clients outside of handler
llm = Bedrock(model_id=model_id, streaming=True)
prompt = PromptTemplate.from_template(prompt_template)
boto3_session = boto3.session.Session()
