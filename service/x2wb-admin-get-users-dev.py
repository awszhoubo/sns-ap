import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('x_user_login_dev')

def lambda_handler(event, context):
    try:
        items = []
        response = table.scan(
            ProjectionExpression="user_name, person_name, email_address, company_name"
        )

        items.extend(response.get('Items', []))

        # 处理 scan 分页
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression="user_name, person_name, email_address, company_name",
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response.get('Items', []))

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps(items)
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": str(e)
            })
        }
