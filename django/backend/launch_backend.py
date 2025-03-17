#!/usr/env/bin python

import os

from dotenv import load_dotenv
from zihelper import aws
from zihelper import utils

load_dotenv()

# Define variables for setup of custom init protocol for DB
DJANGO_INIT_SCRIPT_KEY=utils.load_check_env_var('DJANGO_INIT_SCRIPT_KEY')
DJANGO_INIT_SCRIPT_BUCKET=utils.load_check_env_var('DJANGO_INIT_SCRIPT_BUCKET')
DJANGO_INIT_SCRIPT_LOCAL=utils.load_check_env_var('DJANGO_INIT_SCRIPT_LOCAL')

# Set up the Django environment
os.system('python manage.py makemigrations scrnaseq')
os.system('python manage.py migrate --fake-initial') # In case of migration issues due to existing tables

aws_s3 = aws.AwsS3()

if DJANGO_INIT_SCRIPT_KEY and DJANGO_INIT_SCRIPT_BUCKET:
    aws_s3.download_key_from_bucket(DJANGO_INIT_SCRIPT_BUCKET, DJANGO_INIT_SCRIPT_KEY, 'init_script.py')
    os.system('python3 init_script.py')    

elif DJANGO_INIT_SCRIPT_LOCAL:
    os.system(f'python3 {DJANGO_INIT_SCRIPT_LOCAL}')

os.system('python manage.py createsuperuser')

os.system('gunicorn backend.wsgi:application --bind 0.0.0.0:8000')