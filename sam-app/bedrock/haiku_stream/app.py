import json
import os
import boto3

# environment variables
model_id = os.environ.get("ModelId", "anthropic.claude-3-haiku-20240307-v1:0")

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
    if history:  
        history_str = "\n".join(
            map(
                lambda h: f"{ai_prefix}: {h['content']}"
                if h["type"] == "ai"
                else f"Human: {h['content']}",
                history,
            )
        )
    else:
        history_str=""

    input=body["input"]
    prompt= f"""You are an AI chatbot who is talkative and friendly.
        If you does not know the answer to a question, it truthfully says don't know.
        Current conversation:
        <conversation_history>
        {history_str}
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
    stream = res.get('body')
    if stream:
        for event in stream:
            chunk = event.get('chunk')
            if chunk:
                message = json.loads(chunk.get("bytes").decode())
                
                if message['type'] == "content_block_delta":
                    generated_text = message['delta']['text'] or ""
                    history[-1]["content"] += generated_text
                    apigw.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps({"kind": "token", "chunk": generated_text}),
                    )
                elif message['type'] == "content_block_stop":
                    generated_text = "\n"
                    history[-1]["content"] += generated_text
                    apigw.post_to_connection(
                        ConnectionId=connection_id,
                        Data=json.dumps({"kind": "token", "chunk": generated_text}),
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