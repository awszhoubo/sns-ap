import json
import boto3
import bcrypt
from botocore.exceptions import ClientError

# DynamoDB client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('x_user_login_dev')

def lambda_handler(event, context):
    print("Received event:", json.dumps(event))
    print("Received context:", context)
    try:
        # 解析请求体
        body = json.loads(event.get("body", "{}"))
        username = body.get("username", "").strip()
        password = body.get("password", "").strip()
        email = body.get("email", "").strip()
        personname = body.get("personName", "").strip()
        companyname = body.get("companyName", "").strip()

        # 基本校验
        if not username or not password or not email:
            return response(400, {"message": "用户名、密码和Email不能为空"})

        if len(username) < 3:
            return response(400, {"message": "用户名至少3个字符"})

        if len(password) < 8:
            return response(400, {"message": "密码至少8位"})

        # bcrypt 加密密码
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # print(f"Hashed password: {password_hash}")
        # 插入到 DynamoDB
        item = {
            "user_name": username,
            "password_hash": password_hash,
            "person_name": personname,
            "company_name": companyname,
            "email_address": email
        }

        table.put_item(Item=item)

        print("Item inserted successfully")
        return response(200, {"statusCode": 200, "message": "登録成功", "user_name": username})

    except ClientError as e:
        return response(500, {"statusCode": 500, "message": "DynamoDB エラー", "error": str(e)})
    except Exception as e:
        print(f"Unexpected error: {e}")
        return response(500, {"statusCode": 500, "message": "未知エラー", "error": str(e)})


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"  # 允许CORS
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
