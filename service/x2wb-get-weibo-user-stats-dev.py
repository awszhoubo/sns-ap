import json
import boto3
from collections import defaultdict

s3 = boto3.client('s3')
BUCKET_NAME = 'x2wb-bucket-dev'

def lambda_handler(event, context):
    user_id = event["pathParameters"].get("userId")
    print("user_id: ", user_id)
    if not user_id:
        return respond(400, {"message": "Missing userId path parameter"})

    prefix = f"weibo/{user_id}/"
    print("prefix: ", prefix)
    paginator = s3.get_paginator('list_objects_v2')

    stats = defaultdict(int)

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=prefix):
        for obj in page.get('Contents', []):
            key = obj['Key']
            print("key: ", key)
            if not key.endswith('_zh.txt'):
                continue

            parts = key.split('/')

            print(parts)
            post_date = parts[2]
            print(post_date)
            stats[post_date] += 1

    # 日期排序
    sorted_stats = dict(sorted(stats.items()))

    print(sorted_stats)
    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
        "body": json.dumps(sorted_stats)
    }
