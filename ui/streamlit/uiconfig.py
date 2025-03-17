import os
from enum import Enum

from dotenv import load_dotenv

from zihelper import utils

class AuthMethod(Enum):
    BASIC = "BASIC"

load_dotenv()

BACKEND_API_ENDPOINT = utils.load_check_env_var('BACKEND_API_ENDPOINT').rstrip('/') # Remove trailing slash for format list URL
AUTH_METHOD = AuthMethod.BASIC
AUTH_USER_GROUP = "appuser"

ACCESS_TOKEN_REFESH_SECONDS = 55
