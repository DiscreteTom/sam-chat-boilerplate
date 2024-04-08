import json
import os
import boto3

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
session = boto3.session.Session()
ddb = session.resource("dynamodb")
table = ddb.Table(session_table_name)
bedrock = session.client("bedrock-runtime")


def handler(event, context):
    # print(json.dumps(event))
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]
    connection_id = event["requestContext"]["connectionId"]
    body = json.loads(event["body"])

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
    prompt = prompt_template.format(history=history_str, input=body["input"])
    print(f"prompt:\n{prompt}")
    res = bedrock.invoke_model_with_response_stream(
        modelId=model_id,
        body=json.dumps(
            {
                "prompt": prompt,
                "max_tokens_to_sample": 300,
                "temperature": 0.5,
                "top_k": 250,
                "top_p": 1,
                "stop_sequences": ["\n\nHuman:"],
                "anthropic_version": "bedrock-2023-05-31",
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
