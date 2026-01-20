import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("x_account_register_dev")

def lambda_handler(event, context):
    try:
        userName = event.get("requestContext", {}).get("authorizer", {}).get("username", "unknown") 
        print(userName)
        # 查询指定 user_name 的所有 items，只返回指定字段
        response = table.query(
            KeyConditionExpression=Key("user_name").eq(userName),
            FilterExpression=Attr("china_sns_name").eq("xiaohongshu"),
            ProjectionExpression="customer_name, xiaohongshu_uid, china_sns_url, i_photo"
        )

        items = response.get("Items", [])
        
        users = [
            {
                "xiaohongshu_uid": item.get("xiaohongshu_uid", ""),
                "customer_name": item.get("customer_name", ""),
                "china_sns_url": item.get("china_sns_url", ""),
                "i_photo": item.get("i_photo", "")
            }
            for item in items
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
