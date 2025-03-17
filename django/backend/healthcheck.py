# case-scrnaseq/django/backend/healthcheck.py

import sys
import os

import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

from zihelper import utils
from zihelper import aws

__author__ = "Jonathan Alles"
__email__ = "Jonathan.Alles@evo-byte.com"
__copyright__ = "Copyright 2024"

load_dotenv()

SERVICE_USER_HEALTHCHECK_SECRET_KEY_NAME=utils.load_check_env_var('SERVICE_USER_HEALTHCHECK_SECRET_KEY_NAME')
SERVICE_USER_HEALTHCHECK=utils.load_check_env_var('SERVICE_USER_HEALTHCHECK')
SERVICE_USER_HEALTHCHECK_PWD=utils.load_check_env_var('SERVICE_USER_HEALTHCHECK_PWD')

BACKEND_URL = 'http://localhost:8000/api_v1/'

VIEWS_CHECK = ['fastq_datasets', 'scrnaseq_datasets', 'scrnaseq_integration']

def check_health_view(backend_url: str, view_name: str, login: HTTPBasicAuth) -> bool:
    """Check of REST API Url can be reached 

    Perform list get request to backend URL and check if status code is 200
    Use login HTTPBasicAuth object for authentication
    
    Args:
        backend_url: UR of backend
        view_name: View name check
        login: username and password for authentication

    Returns:
        True if status code is 200, False otherwise
    """
    
    res = requests.get(os.path.join(backend_url, view_name), auth=login)
    if res.status_code != 200:
        print(f"""Healthcheck failed: Could not connect to backend URL {backend_url} 
              view {view_name} with status code {res.status_code}""")
        return False
    return True    
    
def healthcheck() -> int:
    """Run django backend healthcheck

    Perform GET REST API requests to backend URL and check if status code is 200
    Return 0 if all views are reachable, 1 otherwise 
    
    Backend, views and login credentials are defined in environment variables
    
    Returns:
        int: health status
    """
    
    if SERVICE_USER_HEALTHCHECK_SECRET_KEY_NAME:
        aws_secrets_manager = aws.AwsSecretsManager()
        secret_key_json = aws_secrets_manager.get_secret_value_json(SERVICE_USER_HEALTHCHECK_SECRET_KEY_NAME)
        service_user_name = secret_key_json['username']
        service_user_pwd = secret_key_json['password']    
    else:
        service_user_pwd = SERVICE_USER_HEALTHCHECK_PWD
        service_user_name = SERVICE_USER_HEALTHCHECK
    login = HTTPBasicAuth(service_user_name, service_user_pwd)

    for view in VIEWS_CHECK:
        if not check_health_view(BACKEND_URL, view, login):
            return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(healthcheck())