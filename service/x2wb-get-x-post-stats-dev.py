import json
import boto3
from collections import defaultdict

s3 = boto3.client('s3')
BUCKET_NAME = 'x2wb-bucket-dev'

def lambda_handler(event, context):
    
    INCLUDE_PREFIXES = (
        'weibo/',
    )

    paginator = s3.get_paginator('list_objects_v2')

    stats = defaultdict(int)

    for page in paginator.paginate(Bucket=BUCKET_NAME):
        for obj in page.get('Contents', []):
            key = obj['Key']
            if not key.startswith(INCLUDE_PREFIXES):
                continue

            if not key.endswith('_zh.txt'):
                continue

            parts = key.split('/')

            post_date = parts[2]
            stats[post_date] += 1

    # 日期排序
    sorted_stats = dict(sorted(stats.items()))

    print(sorted_stats)
    return {
        "statusCode": 200,
        "headers": {"Access-Control-Allow-Origin": "*", "Content-Type": "application/json"},
        "body": json.dumps(sorted_stats)
    }
