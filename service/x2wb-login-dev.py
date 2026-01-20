import json
import jwt
import datetime
import bcrypt
import boto3
from botocore.exceptions import ClientError

SECRET_KEY = "your-secret-key"
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('x_user_login_dev')

def authentication(username, password):
    
    try:
        response = table.get_item(
            Key={'user_name': username}
        )

        item = response.get('Item')
        if item:
            checked = bcrypt.checkpw(password.encode(), item['password_hash'].encode())
            return checked
        else:
            print("User not found.")
            return False

    except ClientError as e:
        print("DynamoDB ClientError:", e.response['Error']['Message'])
        return False


def lambda_handler(event, context):
    username = event['username']
    password = event['password']

    if authentication(username, password):
        token = jwt.encode(
            {
                "sub": username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
            },
            SECRET_KEY,
            algorithm="HS256"
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"token": token})
        }
    else:
        return {
            "statusCode": 401,
            "body": "Unauthorized"
        }
