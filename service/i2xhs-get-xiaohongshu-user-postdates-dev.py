import json
import boto3

s3 = boto3.client("s3")
BUCKET_NAME = "i2xhs-bucket-dev"

def lambda_handler(event, context):
    user_id = event["pathParameters"].get("userId")
    if not user_id:
        return respond(400, {"message": "Missing userId path parameter"})

    prefix = f"xiaohongshu/{user_id}/"
    try:
        paginator = s3.get_paginator("list_objects_v2")
        prefix_set = set()
        
        for page in paginator.paginate(
            Bucket=BUCKET_NAME,
            Prefix=prefix,
            Delimiter="/"
        ):
            for cp in page.get("CommonPrefixes", []):
                p = cp.get("Prefix", "")
                date = p[len(prefix):-1]  # strip user_id/ and trailing slash
                if date:
                    prefix_set.add(date)

        post_dates = sorted(prefix_set)
        return respond(200, {"post_date_list": post_dates})

    except Exception as e:
        print("Error listing post dates:", e)
        return respond(500, {"message": "Internal server error", "error": str(e)})

def respond(status, body):
    return {
        "statusCode": status,
        "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
        "body": json.dumps(body)
    }
