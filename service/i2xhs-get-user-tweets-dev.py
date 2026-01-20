import json
import boto3
from boto3.dynamodb.conditions import Key, Attr

def get_posts_by_user(user_id, post_date):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('i_user_post_dev')

    try:
        response = table.query(
            KeyConditionExpression=Key('user_id').eq(user_id),
            FilterExpression=Attr('post_date').eq(post_date),
            ProjectionExpression="post_date, post_id"
        )

        return response.get('Items', [])

    except Exception as e:
        print("Error querying posts:", str(e))
        return []


def lambda_handler(event, context):
    print(event)
    print(context)
    user_id = event['pathParameters']['userId']  # /i/users/{userId}/tweets
    query_params = event.get("queryStringParameters", {})
    post_date = query_params.get("post_date")

    posts = get_posts_by_user(user_id, post_date)

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization"
        },
        "body": json.dumps(posts)
    }
