import json
import boto3
from boto3.dynamodb.conditions import Key

scheduler = boto3.client("scheduler")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("x_account_register_dev")
table2 = dynamodb.Table("x_weibo_user_token_dev")


def check_weibo_bind(weibo_uid):
    response2 = table2.get_item(
        Key={
            'user_name': weibo_uid
        },
        ProjectionExpression="weibo_uid"
    )
    item2 = response2.get("Item")
    if item2:
        return "yes"
    else:
        return "no"


def lambda_handler(event, context):
    try:
        userName = event.get("requestContext", {}).get("authorizer", {}).get("username", "unknown") 
        print(userName)
        # 查询指定 user_name 的所有 items，只返回指定字段
        response = table.query(
            KeyConditionExpression=Key("user_name").eq(userName),
            ProjectionExpression=(
                "customer_name, japan_sns_name, japan_sns_url, x_display_name, x_photo, i_photo, "
                "customer_id, china_sns_name, china_sns_url, weibo_uid, xiaohongshu_uid, forbid_keyword, "
                "account_valid_flag, auto_post, manual_post, payment_method, job_name"
            )
        )

        items = response.get("Items", [])
        
        users = []

        for item in items:
            wb_bind = "no"
            wb_uid = item.get("weibo_uid", "")
            if wb_uid:
                wb_bind = check_weibo_bind(wb_uid)

            xiaohongshu_uid = item.get("xiaohongshu_uid", "")
            if xiaohongshu_uid:
                wb_bind = "yes"

            users.append({
                "customer_name": item.get("customer_name", ""),
                "japan_sns_name": item.get("japan_sns_name", ""),
                "japan_sns_url": item.get("japan_sns_url", ""),
                "x_display_name": item.get("x_display_name", ""),
                "x_photo": item.get("x_photo", ""),
                "i_photo": item.get("i_photo", ""),
                "customer_id": item.get("customer_id", ""),
                "china_sns_name": item.get("china_sns_name", ""),
                "china_sns_url": item.get("china_sns_url", ""),
                "weibo_uid": item.get("weibo_uid", ""),
                "xiaohongshu_uid": item.get("xiaohongshu_uid", ""),
                "forbid_keyword": item.get("forbid_keyword", ""),
                "account_valid_flag": item.get("account_valid_flag", ""),
                "auto_post": item.get("auto_post", ""),
                "manual_post": item.get("manual_post", ""),
                "payment_method": item.get("payment_method", "クレジットカード"),
                "weibo_bind": wb_bind
            })

            """
            job_name = item.get("job_name", "")
            state = None

            if job_name:
                try:
                    schedule_resp = scheduler.get_schedule(
                        Name=job_name,
                        GroupName="default"
                    )
                    state = schedule_resp.get("State", None)
                except scheduler.exceptions.ResourceNotFoundException:
                    state = "NOT_FOUND"
                except Exception as e:
                    state = f"ERROR: {str(e)}"

                wb_bind = "no"
                wb_uid = item.get("weibo_uid", "")
                if wb_uid:
                    wb_bind = check_weibo_bind(wb_uid)

                users.append({
                    "customer_name": item.get("customer_name", ""),
                    "japan_sns_name": item.get("japan_sns_name", ""),
                    "japan_sns_url": item.get("japan_sns_url", ""),
                    "x_display_name": item.get("x_display_name", ""),
                    "x_photo": item.get("x_photo", ""),
                    "customer_id": item.get("customer_id", ""),
                    "china_sns_name": item.get("china_sns_name", ""),
                    "china_sns_url": item.get("china_sns_url", ""),
                    "weibo_uid": item.get("weibo_uid", ""),
                    "forbid_keyword": item.get("forbid_keyword", ""),
                    "account_valid_flag": item.get("account_valid_flag", ""),
                    "auto_post": item.get("auto_post", ""),
                    "manual_post": item.get("manual_post", ""),
                    "job_name": job_name,
                    "job_state": state,
                    "weibo_bind": wb_bind
                })
            """
            
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
