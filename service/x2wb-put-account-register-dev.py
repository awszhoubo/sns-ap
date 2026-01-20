import json
import requests
import boto3
from datetime import datetime, timezone, timedelta
from botocore.exceptions import NoCredentialsError, ClientError

scheduler = boto3.client("scheduler")
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('x_account_register_dev')
PAGE_ACCESS_TOKEN = "EAAMMrDX9iwUBPsoMuUYbw3zIuTgJqfaqsZCgw5gyQhjnNGyd6mwArnxIvKP3ZCsqw3q2IHdEZBNEoZAI6nCLGDLpZCONRlOk3ZCvYpCHQT1U5hp4MHHYx3IjIl9wZASngu9skGIedTkAZBB5qWT0bqUebEPvscKqZCpS6o3QczvXA8e3FJsOg3ZBySAgAzWqIWpLxWxY5i"
PAGE_ID = "749170468288927"


def get_secret():

    secret_name = "dev/x2wb"
    region_name = "ap-northeast-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


def lambda_handler(event, context):
    # 解析请求体
    body = json.loads(event.get("body", "{}"))
    japanSnsName = body.get("japanSnsName", "").strip()
    if japanSnsName == "x":
        return x_handler(event, context)
    else:
        return instagram_handler(event, context)


def instagram_handler(event, context):

    try:
        # 解析请求体
        body = json.loads(event.get("body", "{}"))
        userName = event.get("requestContext", {}).get("authorizer", {}).get("username", "unknown")

        customerName = body.get("customerName", "").strip()
        japanSnsName = body.get("japanSnsName", "").strip()
        japanSnsUrl = body.get("japanSnsUrl", "").strip()
        chinaSnsName = body.get("chinaSnsName", "").strip()
        chinaSnsUrl = body.get("chinaSnsUrl", "").strip()
        forbidKeyword = body.get("forbidKeyword", "").strip()
        accountValidFlag = body.get("accountValidFlag", "").strip()
        autoPost = body.get("autoPost", "").strip()
        manualPost = body.get("manualPost", "").strip()
        paymentMethod = body.get("paymentMethod", "").strip()
        # Get Tokyo time (UTC+9)
        JST = timezone(timedelta(hours=9))
        now_jst = datetime.now(JST).isoformat()  # e.g. "2025-07-03T20:21:52+09:00"

        # secret = get_secret()
        # X_BEARER_TOKEN = secret['X_BEARER_TOKEN_1']

        xUrl = japanSnsUrl
        csUrl = chinaSnsUrl

        xiaohongshuUid = csUrl.rstrip("/").split("/")[-1]
        # iName = xUrl.rstrip("/").split("/")[-1]  # NM_NANAPARTY

        # 3. 调用 X API v2 获取用户信息
        # headers = {
        #     "Authorization": f"Bearer {X_BEARER_TOKEN}"
        # }
        # url = f"https://graph.facebook.com/v24.0/me/accounts?access_token={PAGE_ACCESS_TOKEN}"
        
        # resp = requests.get(url, headers=headers)
        # resp = requests.get(url)

        # if resp.status_code != 200:
        #     raise Exception(f"graph API 调用失败: {resp.status_code}, {resp.text}")

        # data = resp.json().get("data", {})
        # PAGE_ID = data.get("id")

        url_page = f"https://graph.facebook.com/v24.0/{PAGE_ID}"
        params_page = {
            "fields": "instagram_business_account",
            "access_token": PAGE_ACCESS_TOKEN
        }
        r1 = requests.get(url_page, params=params_page)
        page_data = r1.json()
        print("Page Info:", page_data)
        ig_user_id = page_data["instagram_business_account"]["id"]

        url_ig = f"https://graph.facebook.com/v24.0/{ig_user_id}"
        params_ig = {
            "fields": "id,username,name,profile_picture_url,biography,followers_count,follows_count,media_count,website",
            "access_token": PAGE_ACCESS_TOKEN
        }
        r2 = requests.get(url_ig, params=params_ig)
        ig_data = r2.json()
        print("Instagram User Info:", ig_data)

        igUserName = ig_data.get("username")
        igName = ig_data.get("name")
        iDisplayName = igName.strip() if igName and igName.strip() else igUserName

        iPhoto = ig_data.get("profile_picture_url")

        schedule_name = f"i2xhs-load-posts-{ig_user_id}-{xiaohongshuUid}-dev"
        # Get Tokyo time (UTC+9)
        schedule_now = datetime.now(JST)
        run_time = schedule_now + timedelta(minutes=10)

        cron_expr = f"cron({run_time.minute} {run_time.hour} ? * * *)"
        respSchedule = scheduler.create_schedule(
            Name=schedule_name,
            GroupName="default",
            Description=f"From {ig_user_id} to {xiaohongshuUid} created by {userName}",
            ScheduleExpression=cron_expr,
            ScheduleExpressionTimezone="Asia/Tokyo",
            FlexibleTimeWindow={"Mode": "OFF"},
            State="ENABLED",
            Target={
                "Arn": "arn:aws:lambda:ap-northeast-1:949084318172:function:i2xhs-load-posts-batch-dev",
                "RoleArn": "arn:aws:iam::949084318172:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_f0c9b1ea3a",
                "Input": json.dumps({"user_id": ig_user_id, "xiaohongshu_uid": xiaohongshuUid}),
                "RetryPolicy": {
                    "MaximumEventAgeInSeconds": 60,
                    "MaximumRetryAttempts": 0
                }
            }
        )

        # 插入到 DynamoDB
        item = {
            "user_name": userName,
            "customer_name": customerName,
            "japan_sns_name": japanSnsName,
            "japan_sns_url": japanSnsUrl,
            "china_sns_name": chinaSnsName,
            "china_sns_url": chinaSnsUrl,
            "forbid_keyword": forbidKeyword,
            "account_valid_flag": accountValidFlag,
            "auto_post": autoPost,
            "manual_post": manualPost,
            "payment_method": paymentMethod,
            "customer_id": ig_user_id,
            "xiaohongshu_uid": xiaohongshuUid,
            "i_display_name": iDisplayName,
            "i_photo": iPhoto,
            "job_name": schedule_name,
            "updated_at": now_jst
        }

        table.put_item(Item=item)
        print("Item inserted successfully")
        return response(200, {"statusCode": 200, "message": "登録成功", "customer_name": customerName})

    except ClientError as e:
        print(f"ClientError error: {e}")
        return response(500, {"statusCode": 500, "message": "DynamoDB エラー", "error": str(e)})
    except Exception as e:
        print(f"Unexpected error: {e}")
        return response(500, {"statusCode": 500, "message": "未知エラー", "error": str(e)})


def x_handler(event, context):

    try:
        # 解析请求体
        body = json.loads(event.get("body", "{}"))
        userName = event.get("requestContext", {}).get("authorizer", {}).get("username", "unknown")

        customerName = body.get("customerName", "").strip()
        japanSnsName = body.get("japanSnsName", "").strip()
        japanSnsUrl = body.get("japanSnsUrl", "").strip()
        chinaSnsName = body.get("chinaSnsName", "").strip()
        chinaSnsUrl = body.get("chinaSnsUrl", "").strip()
        forbidKeyword = body.get("forbidKeyword", "").strip()
        accountValidFlag = body.get("accountValidFlag", "").strip()
        autoPost = body.get("autoPost", "").strip()
        manualPost = body.get("manualPost", "").strip()
        paymentMethod = body.get("paymentMethod", "").strip()
        # Get Tokyo time (UTC+9)
        JST = timezone(timedelta(hours=9))
        now_jst = datetime.now(JST).isoformat()  # e.g. "2025-07-03T20:21:52+09:00"

        secret = get_secret()
        X_BEARER_TOKEN = secret['X_BEARER_TOKEN_1']

        xUrl = japanSnsUrl
        csUrl = chinaSnsUrl

        weiboUid = csUrl.rstrip("/").split("/")[-1]
        xName = xUrl.rstrip("/").split("/")[-1]  # NM_NANAPARTY

        # 3. 调用 X API v2 获取用户信息
        headers = {
            "Authorization": f"Bearer {X_BEARER_TOKEN}"
        }
        url = f"https://api.x.com/2/users/by/username/{xName}?user.fields=profile_image_url,id,name,username"
        
        resp = requests.get(url, headers=headers)

        if resp.status_code != 200:
            raise Exception(f"X API 调用失败: {resp.status_code}, {resp.text}")

        data = resp.json().get("data", {})
        customerId = data.get("id")
        xDisplayName = data.get("name")
        xUserName = data.get("username")  # 应该等于 NM_NANAPARTY
        """
        customerId = "2962468880"
        xDisplayName = "水樹奈々オフィシャル"
        xUserName = "sato"
        # 4. 构造 xPhoto
        xPhoto = "https://pbs.twimg.com/profile_images/1876569848106598400/65GPnZ3w_normal.jpg"
        """
        xPhoto = data.get("profile_image_url")

        schedule_name = f"x2wb-load-posts-batch-{customerId}-{weiboUid}-dev"
        # Get Tokyo time (UTC+9)
        schedule_now = datetime.now(JST)
        run_time = schedule_now + timedelta(minutes=10)

        cron_expr = f"cron({run_time.minute} {run_time.hour} ? * * *)"
        respSchedule = scheduler.create_schedule(
            Name=schedule_name,
            GroupName="default",
            Description=f"From {customerId} to {weiboUid} created by {userName}",
            ScheduleExpression=cron_expr,
            ScheduleExpressionTimezone="Asia/Tokyo",
            FlexibleTimeWindow={"Mode": "OFF"},
            State="ENABLED",
            Target={
                "Arn": "arn:aws:lambda:ap-northeast-1:949084318172:function:x2wb-load-posts-batch-dev",
                "RoleArn": "arn:aws:iam::949084318172:role/service-role/Amazon_EventBridge_Scheduler_LAMBDA_f0c9b1ea3a",
                "Input": json.dumps({"user_id": customerId, "weibo_uid": weiboUid}),
                "RetryPolicy": {
                    "MaximumEventAgeInSeconds": 60,
                    "MaximumRetryAttempts": 0
                }
            }
        )

        # 插入到 DynamoDB
        item = {
            "user_name": userName,
            "customer_name": customerName,
            "japan_sns_name": japanSnsName,
            "japan_sns_url": japanSnsUrl,
            "china_sns_name": chinaSnsName,
            "china_sns_url": chinaSnsUrl,
            "forbid_keyword": forbidKeyword,
            "account_valid_flag": accountValidFlag,
            "auto_post": autoPost,
            "manual_post": manualPost,
            "payment_method": paymentMethod,
            "customer_id": customerId,
            "weibo_uid": weiboUid,
            "x_display_name": xDisplayName,
            "x_photo": xPhoto,
            "job_name": schedule_name,
            "updated_at": now_jst
        }

        table.put_item(Item=item)
        print("Item inserted successfully")
        return response(200, {"statusCode": 200, "message": "登録成功", "customer_name": customerName})

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
