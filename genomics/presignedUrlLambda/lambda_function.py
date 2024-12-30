import json
import boto3
import uuid
import os

def lambda_handler(event, context):
    # Add new parameters to existing parameter list
    file_name = event['queryStringParameters'].get('file_name')
    json_rules = event['queryStringParameters'].get('json_rules')  
    json_static_rules = event['queryStringParameters'].get('json_static_rules')
    # BEGIN NEW PARAMETERS
    column_definitions = event['queryStringParameters'].get('column_definitions')
    static_rule_exclusions = event['queryStringParameters'].get('static_rule_exclusions')
    # END NEW PARAMETERS
    upload_param = event['queryStringParameters'].get('upload')
    uploadTrue = upload_param and upload_param.lower() == 'true'
    unique_id = event['queryStringParameters'].get('uuid')
    sra_param = event['queryStringParameters'].get('sra')
    sraTrue = sra_param and sra_param.lower() == 'true'

    filenameWithoutExtension = os.path.splitext(os.path.basename(file_name))[0]

    if (not file_name) or (not upload_param):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "file_name / upload query parameter is required"})
        }
    
    if (uploadTrue == False) and (not (unique_id or sra_param)):
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "when downloading, search UUID and sra param are required."})
        }

    if uploadTrue:
        unique_id = str(uuid.uuid4())
    fileName = f"{unique_id}_{file_name}"
    if not uploadTrue:
        if sraTrue:
            fileName = f"{unique_id}_{filenameWithoutExtension}_sra{os.path.splitext(os.path.basename(file_name))[1]}"
            mapping_key = f"mappings/{unique_id}_sra.json"
        else:
            fileName = f"{unique_id}_{filenameWithoutExtension}_biosample{os.path.splitext(os.path.basename(file_name))[1]}"
            mapping_key = f"mappings/{unique_id}_biosample.json"

    s3_client = boto3.client(
        's3',
        region_name='us-west-2',
    )
    
    try:
        response = s3_client.list_buckets()
        matching_buckets = [bucket['Name'] for bucket in response['Buckets'] if "genomicsuploaddownload" in bucket['Name']]
        if not matching_buckets:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "No bucket found containing 'genomicsuploaddownload' in the name."})
            }
        bucket_name = matching_buckets[0]
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": f"Failed to list buckets: {str(e)}"})
        }

    if json_rules:
        try:
            json_rules_key = f"{unique_id}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=f"rules/{json_rules_key}",
                Body=json_rules,
                ContentType="application/json"
            )
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Failed to save json_rules: {str(e)}"})
            }

    if json_static_rules:
        try:
            json_static_rules_key = f"static_{unique_id}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=f"rules/{json_static_rules_key}",
                Body=json_static_rules,
                ContentType="application/json"
            )
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Failed to save json_static_rules: {str(e)}"})
            }

    # BEGIN NEW S3 UPLOADS
    if column_definitions:
        try:
            column_definitions_key = f"columndef_{unique_id}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=f"rules/{column_definitions_key}",
                Body=column_definitions,
                ContentType="application/json"
            )
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Failed to save column_definitions: {str(e)}"})
            }

    if static_rule_exclusions:
        try:
            static_rule_exclusions_key = f"exclusions_{unique_id}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=f"rules/{static_rule_exclusions_key}",
                Body=static_rule_exclusions,
                ContentType="application/json"
            )
        except Exception as e:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": f"Failed to save static_rule_exclusions: {str(e)}"})
            }
    # END NEW S3 UPLOADS

    if uploadTrue:
        url = generate_presigned_url(
            s3_client,
            "put_object",
            {"Bucket": bucket_name, "Key": f"upload/{fileName}", 'ContentType': 'text/csv'},
            900
        )
        print("Successful")

        retObj = {
            'url': url,
            'file_name': fileName,
            'uuid': unique_id
        }
    else:
        url = generate_presigned_url(
            s3_client,
            "get_object",
            {"Bucket": bucket_name, "Key": f"download/{fileName}"},
            900
        )
        print("Successful")

        mapping_data = {}
        try:
            response = s3_client.get_object(
                Bucket=bucket_name, Key=mapping_key
            )
            mapping_content = response['Body'].read().decode('utf-8')
            mapping_data = json.loads(mapping_content)
        except Exception as e:
            print(f"Mapping file not found: {str(e)}")

        retObj = {
            'url': url,
            'file_name': fileName,
            'uuid': unique_id,
            'mappings': mapping_data
        }

    return {
        'statusCode': 200,
        'body': json.dumps(retObj)
    }

def generate_presigned_url(s3_client, client_method, method_parameters, expires_in):
    """
    Generate a presigned Amazon S3 URL that can be used to perform an action.

    :param s3_client: A Boto3 Amazon S3 client.
    :param client_method: The name of the client method that the URL performs.
    :param method_parameters: The parameters of the specified client method.
    :param expires_in: The number of seconds the presigned URL is valid for.
    :return: The presigned URL.
    """
    
    try:
        url = s3_client.generate_presigned_url(
            ClientMethod=client_method, Params=method_parameters, ExpiresIn=expires_in
        )
    except Exception:
        raise
    return url