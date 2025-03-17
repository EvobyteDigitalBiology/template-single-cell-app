import json
import boto3
import jmespath
import os
boto3.set_stream_logger('')
client = boto3.client("ecs")

"""
    
"""

def lambda_handler(event, context):
    
    # Load env variables
    cluster_name = os.environ.get('CLUSTER')
    task_definition = os.environ.get('TASK_DEFINITION')
    container_overrides = os.environ.get('CONTAINER_OVERRIDES')
    security_groups = os.environ.get('SECURITY_GROUPS').split(',') # In case multiple are encoded by SECURITY GROUPS
    subnets = os.environ.get('SUBNETS').split(',')
    
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
                {"name": container_overrides, "command": []},
            ],
        },
        propagateTags="TASK_DEFINITION",
        taskDefinition=task_definition
    )
    
    return {'statusCode' : 200,
        'body': json.dumps(
            f'success'
            )
    }