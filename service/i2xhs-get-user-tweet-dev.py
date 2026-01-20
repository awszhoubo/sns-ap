import boto3
import json
import os
import urllib.parse

s3 = boto3.client("s3")
BUCKET_NAME = "i2xhs-bucket-dev"

def lambda_handler(event, context):
    try:
        path_params = event.get("pathParameters", {})
        query_params = event.get("queryStringParameters", {})

        user_id = path_params.get("userId")
        post_id = path_params.get("tweetId")
        post_date = query_params.get("post_date")

        if not (user_id and post_id and post_date):
            return respond(400, {"error": "Missing userId, postId or post_date"})

        base_prefix = f"{user_id}/{post_date}/{post_id}"
        ja_key = f"{base_prefix}/{post_id}_ja.txt"
        zh_key = f"{base_prefix}/{post_id}_zh.txt"
        image_prefix = f"{base_prefix}/image/"
        video_prefix = f"{base_prefix}/video/"

        # Get JA and ZH text content
        post_ja = get_text_from_s3(ja_key)
        post_zh = get_text_from_s3(zh_key)

        # Get image URLs
        image_urls = get_presigned_image_urls(image_prefix, post_id)
        video_urls = get_presigned_image_urls(video_prefix, post_id)

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table("i_user_post_dev")

        response = table.get_item(
            Key={
                'user_id': user_id,
                'post_id': post_id
            }
        )

        ai_selected = ""
        
        item = response.get('Item')
        if item:
            ai_selected = item.get("ai_selected", "")

        return respond(200, {
            "ai_selected": ai_selected,
            "post_ja": post_ja,
            "post_zh": post_zh,
            "images": image_urls,
            "videos": video_urls
        })

    except Exception as e:
        print("Error:", str(e))
        return respond(500, {"error": "Internal server error", "message": str(e)})

def get_text_from_s3(key):
    try:
        response = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        return response["Body"].read().decode("utf-8")
    except s3.exceptions.NoSuchKey:
        return None
    except Exception as e:
        print(f"Error reading {key}: {e}")
        return None

def get_presigned_image_urls(prefix, post_id):
    urls = []
    try:
        result = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=prefix)
        for obj in result.get("Contents", []):
            key = obj["Key"]
            if f"{post_id}" in os.path.basename(key):
                url = s3.generate_presigned_url("get_object", Params={
                    "Bucket": BUCKET_NAME,
                    "Key": key
                }, ExpiresIn=3600)  # 1 hour
                urls.append(url)
    except Exception as e:
        print(f"Error listing images in {prefix}: {e}")
    return urls

def respond(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "application/json"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
