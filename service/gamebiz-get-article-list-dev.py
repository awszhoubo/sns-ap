import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

def scan_all_items():
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('gamebiz_article_dev')

        items = []
        response = table.scan(
            ProjectionExpression="article_id, publish_time"    
        )
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.scan(
                ExclusiveStartKey=response["LastEvaluatedKey"]
            )
            items.extend(response.get("Items", []))

        return items
    except Exception as e:
        print("Error scanning table:", str(e))
        return []


def lambda_handler(event, context):
    posts = scan_all_items()
    print(posts)
    
    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization"
        },
        "body": json.dumps(posts)
    }
