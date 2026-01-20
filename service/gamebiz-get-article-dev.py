import boto3
import json
import os
import urllib.parse

s3 = boto3.client("s3")
BUCKET_NAME = "snsap-crawler-dev"

def lambda_handler(event, context):
    try:
        path_params = event.get("pathParameters", {})
        article_id = path_params.get("articleId")

        if not (article_id):
            return respond(400, {"error": "Missing articleId"})

        base_prefix = f"gamebiz/gamebiz_tag_22096/{article_id}"
        ja_key = f"{base_prefix}/article_{article_id}_ja.md"
        zh_key = f"{base_prefix}/article_{article_id}_zh.md"
        image_prefix = f"{base_prefix}/images/"

        # Get JA and ZH text content
        post_ja = get_text_from_s3(ja_key)
        post_zh = get_text_from_s3(zh_key)

        # Get image URLs
        image_urls = get_presigned_image_urls(image_prefix, article_id)

        return respond(200, {
            "post_ja": post_ja,
            "post_zh": post_zh,
            "images": image_urls
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
            if f"{post_id}_" in os.path.basename(key):
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
