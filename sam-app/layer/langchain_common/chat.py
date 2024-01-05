import json
from boto3 import Session
from langchain.memory.chat_message_histories import DynamoDBChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from langchain.llms.base import LLM
from callback import APIGatewayWebSocketCallbackHandler


def chat(
    event: dict,
    llm: LLM,
    boto3_session: Session,
    session_table_name: str,
    ai_prefix: str,
    prompt: PromptTemplate,
):
    # print(json.dumps(event))
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    connection_id = event["requestContext"]["connectionId"]
    body = json.loads(event["body"])

    # set callback handler
    # so that every time the model generates a chunk of response,
    # it is sent to the client
    callback = APIGatewayWebSocketCallbackHandler(
        boto3_session,
        f"https://{domain}/{stage}",
        connection_id,
        on_token=lambda t: json.dumps({"kind": "token", "chunk": t}),
        on_end=lambda: json.dumps({"kind": "end"}),
        on_err=lambda e: json.dumps({"kind": "error"}),
    )
    llm.callbacks = [callback]

    history = DynamoDBChatMessageHistory(
        table_name=session_table_name,
        session_id=connection_id,
        boto3_session=boto3_session,
    )
    memory = ConversationBufferMemory(ai_prefix=ai_prefix, chat_memory=history)
    conversation = ConversationChain(llm=llm, memory=memory)
    conversation.prompt = prompt

    conversation.predict(input=body["input"])
