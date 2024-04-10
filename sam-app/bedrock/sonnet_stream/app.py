import json
import os
import boto3

# environment variables
model_id = os.environ.get("ModelId", "anthropic.claude-3-sonnet-20240229-v1:0")

session_table_name = os.environ["SessionTableName"]

ai_prefix = os.environ.get(
    "AI_Prefix",
    # by default (Claude), this is "Assistant"
    "Assistant",
)

system_prompt = """You are Claude, an AI assistant created by Anthropic to be helpful,harmless, and honest. Your goal is to provide informative and substantive responses to queries while avoiding potential harms."""

# init clients outside of handler
session = boto3.session.Session()
ddb = session.resource("dynamodb")
table = ddb.Table(session_table_name)
bedrock = session.client("bedrock-runtime")

def handler(event, context):
    # print(json.dumps(event))
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    connection_id = event["requestContext"]["connectionId"]
    body_str = event["body"]
    if not body_str:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid request payload"}),
        }

    try:
        # 将请求体字符串解析为 JSON 对象
        body = json.loads(body_str)
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON payload"}),
        }

    # 检查请求体是否包含所需的字段
    if "action" not in body or "input" not in body:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid request payload"}),
        }
    apigw = session.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{domain}/{stage}",
    )

    # get chat history from ddb
    history = []
    try:
        res = table.get_item(Key={"SessionId": connection_id})
        history = res["Item"]["History"]
    except:
        pass

    # append this conversation
    history.append({"type": "human", "content": body["input"]})
    history.append({"type": "ai", "content": ""})

    # invoke bedrock
    history_str = "\n".join(
        map(
            lambda h: f"{ai_prefix}: {h['content']}"
            if h["type"] == "ai"
            else f"Human: {h['content']}",
            history,
        )
    )
    history=history_str
    input=body["input"]

    prompt = f"""You are an AI chatbot who is talkative and friendly.
        If you does not know the answer to a question, it truthfully says don't know.
        Current conversation:
        <conversation_history>
        {history}
        </conversation_history>
        Then provide answer for {input}
        """
    #prompt = prompt_template.format(history=history_str, input=body["input"])

    print(f"prompt:\n{prompt}")
    res = bedrock.invoke_model_with_response_stream(
        modelId=model_id,
        body=json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 20480,
            "temperature": 0.1,
            "top_k": 250,
            "top_p": 1,
            "stop_sequences": ["\n\nHuman"],
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        ),
    )

    # stream response to client
    for data in res["body"]:
        # print(json.dumps(data))
        completion = json.loads(data["chunk"]["bytes"])["completion"]
        history[-1]["content"] += completion
        apigw.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"kind": "token", "chunk": completion}),
        )
    apigw.post_to_connection(
        ConnectionId=connection_id,
        Data=json.dumps({"kind": "end"}),
    )

    # write history to ddb
    table.put_item(Item={"SessionId": connection_id, "History": history})

    return {
        "statusCode": 200,
    }