# case-scrnaseq/django/backend/settings/development.py

import os
from datetime import timedelta

from dotenv import load_dotenv

from zihelper import aws
from zihelper import utils

from .base import *

# Load dotenv variables from base
load_dotenv()

# Load database logins from AWS Secrets Manager (or .env)
django_secret_key_name = utils.load_check_env_var('DJANGO_SECRET_KEY_NAME')
db_log_secret_name = utils.load_check_env_var('DB_LOG_SECRET_NAME')

aws_secrets_manager = aws.AwsSecretsManager()

if django_secret_key_name:
    django_secret_key_json = aws_secrets_manager.get_secret_value_json(django_secret_key_name)
    SECRET_KEY = django_secret_key_json['SECRET_KEY']
else:
    SECRET_KEY = utils.load_check_env_var('SECRET_KEY')    

if db_log_secret_name:
    db_log_secret_json = aws_secrets_manager.get_secret_value_json(db_log_secret_name)
    DB_USER = db_log_secret_json["username"]
    DB_PASSWORD = db_log_secret_json["password"]
else:
    DB_USER = utils.load_check_env_var("DB_USER")
    DB_PASSWORD = utils.load_check_env_var("DB_PASSWORD")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = utils.load_check_env_var('ALLOWED_HOSTS').split(',')

DB_HOST = utils.load_check_env_var('DB_HOST')
DB_NAME = utils.load_check_env_var('DB_NAME')

# Can be used to switch production and test databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': '5432',
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(seconds=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": False,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("Bearer","JWT"),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),

    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}