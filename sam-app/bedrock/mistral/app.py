import json
import os
import boto3

# environment variables
model_id = os.environ.get("ModelId", "mistral.mistral-large-2402-v1:0")

session_table_name = os.environ["SessionTableName"]

ai_prefix = os.environ.get(
    "AI_Prefix",
    # by default (Claude), this is "Assistant"
    "Assistant",
)

prompt_template = os.environ.get(
    "PromptTemplate",
    # by default (Claude)
    "\\n<s>[INST] {input} [/INST]\\n",
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
    body = event["body"]

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
    res = bedrock.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "prompt": prompt,
            "max_tokens": 4000,
            "temperature": 0.2,
            "top_p": 0.7,
            "top_k": 50
        })
    )

    response_body = json.loads(res.get('body').read())
    outputs = response_body.get('outputs')
    
    for index, output in enumerate(outputs):
        outtext = output['text']
        history[-1]["content"] += outtext
        apigw.post_to_connection(
            ConnectionId=connection_id,
            Data=json.dumps({"kind": "output", "chunk": outtext}),
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