import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("x_account_register_dev")
table2 = dynamodb.Table("x_weibo_user_token_dev")

def check_weibo_bind(weibo_uid):
    if weibo_uid == "":
        return False

    response2 = table2.get_item(
        Key={
            'user_name': weibo_uid
        },
        ProjectionExpression="weibo_uid"
    )
    item2 = response2.get("Item")

    if item2:
        return True
    else:
        return False


def lambda_handler(event, context):
    try:
        userName = event.get("requestContext", {}).get("authorizer", {}).get("username", "unknown") 
        print(userName)
        # 查询指定 user_name 的所有 items，只返回指定字段
        response = table.query(
            KeyConditionExpression=Key("user_name").eq(userName),
            FilterExpression=Attr("china_sns_name").eq("weibo"),
            ProjectionExpression="customer_name, weibo_uid, china_sns_url, x_photo"
        )

        items = response.get("Items", [])
        
        users = [
            {
                "weibo_uid": item.get("weibo_uid", ""),
                "customer_name": item.get("customer_name", ""),
                "china_sns_url": item.get("china_sns_url", ""),
                "x_photo": item.get("x_photo", "")
            }
            for item in items
            if check_weibo_bind(item.get("weibo_uid", ""))
        ]
        
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"  # 允许CORS
            },
            "body": json.dumps(users, ensure_ascii=False)
        }

    except Exception as e:
        print("Error querying table:", str(e))
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Internal Server Error"})
        }
