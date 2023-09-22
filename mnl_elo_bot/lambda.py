import json
from elo_bot import main


def handler(event, context):
    query = event["queryStringParameters"]
    main(
        query.get("post", False),
        query.get("channel", "tests"),
        query.get("message", ""),
    )
    return {"statusCode": 200, "body": json.dumps("posted")}
