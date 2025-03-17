import json
import boto3
import jmespath
import os
boto3.set_stream_logger('')
client = boto3.client("ecs")

"""

"""

def lambda_handler(event, context):
    
    # Get object key
    object_key = jmespath.search('Records[0].s3.object.key', event)
    bucket = jmespath.search('Records[0].s3.bucket.name', event)
    
    # Load env variables
    # Load env variables
    cluster_name = os.environ.get('CLUSTER')
    task_definition = os.environ.get('TASK_DEFINITION')
    container_overrides = os.environ.get('CONTAINER_OVERRIDES')
    security_groups = os.environ.get('SECURITY_GROUPS').split(',') # In case multiple are encoded by SECURITY GROUPS
    subnets = os.environ.get('SUBNETS').split(',')
    object_key_cmd_argument = os.environ.get('OBJECT_KEY_CMD_ARGUMENT')
    bucket_cmd_argument = os.environ.get('BUCKET_CMD_ARGUMENT')
    
    # Add overwrites
    overwrite_cmd = [bucket_cmd_argument, bucket, object_key_cmd_argument, object_key]
    
    res = client.run_task(
        cluster=cluster_name,
        count=1,
        enableECSManagedTags=False,
        enableExecuteCommand=False,
        launchType="FARGATE",
        networkConfiguration={
            "awsvpcConfiguration": {
                "securityGroups": security_groups,
                "subnets": subnets
            }
        },
        overrides={
            "containerOverrides": [
                {"name": container_overrides, "command": overwrite_cmd},
            ],
        },
        propagateTags="TASK_DEFINITION",
        taskDefinition=task_definition
    )
    
    return {'statusCode' : 200,
        'body': json.dumps(
            f'{bucket_cmd_argument}: {bucket}, {object_key_cmd_argument}: {object_key}'
            )
    }