import json
import boto3
from botocore.exceptions import ClientError

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("x_account_register_dev")


def lambda_handler(event, context):
    try:
        # ===== 1. 取得登录用户（Partition Key）=====
        user_name = (
            event.get("requestContext", {})
            .get("authorizer", {})
            .get("username", "unknown")
        )

        if user_name == "unknown":
            return response(401, {"message": "Unauthorized"})

        # ===== 2. 解析请求 Body =====
        body = json.loads(event.get("body", "{}"))

        customer_name = body.get("customer_name")
        if not customer_name:
            return response(400, {"message": "customer_name is required"})

        # ===== 3. 可更新字段 =====
        update_fields = {
            "forbid_keyword": body.get("forbid_keyword"),
            "auto_post": body.get("auto_post"),
            "manual_post": body.get("manual_post"),
            "payment_method": body.get("payment_method"),
        }

        # 过滤掉 None（只更新传入的字段）
        update_fields = {k: v for k, v in update_fields.items() if v is not None}

        if not update_fields:
            return response(400, {"message": "No fields to update"})

        # ===== 4. 构建 UpdateExpression =====
        update_expression = "SET " + ", ".join(
            f"#{k} = :{k}" for k in update_fields
        )

        expression_attribute_names = {
            f"#{k}": k for k in update_fields
        }

        expression_attribute_values = {
            f":{k}": v for k, v in update_fields.items()
        }

        # ===== 5. 执行 DynamoDB Update =====
        table.update_item(
            Key={
                "user_name": user_name,
                "customer_name": customer_name
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ConditionExpression="attribute_exists(user_name) AND attribute_exists(customer_name)"
        )

        return response(200, {"message": "Update successful"})

    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return response(404, {"message": "Record not found"})
        else:
            print("DynamoDB Error:", e)
            return response(500, {"message": "DynamoDB error"})

    except Exception as e:
        print("Unexpected Error:", e)
        return response(500, {"message": "Internal server error"})


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(body, ensure_ascii=False)
    }
