#!/usr/env/bin python
 
import os
import django

from dotenv import load_dotenv

from zihelper import aws
from zihelper import utils

load_dotenv()

# Set up the Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.getenv('DJANGO_SETTINGS_MODULE'))
django.setup()

from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.contrib.auth.hashers import make_password, PBKDF2PasswordHasher

print("Run init script to configure service user and permissions")

print("Setup permissions....")

# Create permissions
add_fastqdatasets, created = Permission.objects.get_or_create(codename = 'add_fastqdatasets')
change_fastqdatasets, created = Permission.objects.get_or_create(codename = 'change_fastqdatasets')
view_fastqdatasets, created = Permission.objects.get_or_create(codename = 'view_fastqdatasets')

add_scrnaseq_dataset, created = Permission.objects.get_or_create(codename = 'add_scrnaseqdatasets')
change_scrnaseq_dataset, created = Permission.objects.get_or_create(codename = 'change_scrnaseqdatasets')
view_scrnaseq_dataset, created = Permission.objects.get_or_create(codename = 'view_scrnaseqdatasets')

add_scrnaseq_integration, created = Permission.objects.get_or_create(codename = 'add_scrnaseqintegration')
change_scrnaseq_integration, created = Permission.objects.get_or_create(codename = 'change_scrnaseqintegration')
view_scrnaseq_integration, created = Permission.objects.get_or_create(codename = 'view_scrnaseqintegration')

add_scrnaseq_dataset_annotations, created = Permission.objects.get_or_create(codename = 'add_scrnaseqdatasetannotations')
change_scrnaseq_dataset_annotations, created = Permission.objects.get_or_create(codename = 'change_scrnaseqdatasetannotations')
view_scrnaseq_dataset_annotations, created = Permission.objects.get_or_create(codename = 'view_scrnaseqdatasetannotations')

add_scrnaseq_cluster_annotations, created = Permission.objects.get_or_create(codename = 'add_scrnaseqclusterannotations')
change_scrnaseq_cluster_annotations, created = Permission.objects.get_or_create(codename = 'change_scrnaseqclusterannotations')
view_scrnaseq_cluster_annotations, created = Permission.objects.get_or_create(codename = 'view_scrnaseqclusterannotations')

print("Setup user groups....")

# Create groups
service_group_rw, created = Group.objects.get_or_create(name='service_group_rw')
service_group_r, created = Group.objects.get_or_create(name='service_group_r')
app_user_group, created = Group.objects.get_or_create(name='app_user')


# Add permissions to groups

service_group_r.permissions.set([view_fastqdatasets,
                                  view_scrnaseq_dataset,
                                  view_scrnaseq_integration])

service_group_rw.permissions.set([add_fastqdatasets, change_fastqdatasets, view_fastqdatasets,
                                  add_scrnaseq_dataset, change_scrnaseq_dataset, view_scrnaseq_dataset,
                                  add_scrnaseq_integration, change_scrnaseq_integration, view_scrnaseq_integration])

# App user has read permission and can edit annotation tables
app_user_group.permissions.set([
    view_fastqdatasets,
    view_scrnaseq_dataset,
    view_scrnaseq_integration,
    view_scrnaseq_dataset_annotations,
    add_scrnaseq_dataset_annotations,
    change_scrnaseq_dataset_annotations,
    add_scrnaseq_cluster_annotations,
    change_scrnaseq_cluster_annotations,
    view_scrnaseq_cluster_annotations
])

print("Setup service user....")

aws_secrets_manager = aws.AwsSecretsManager()


# # Load database logins from AWS Secrets Manager (or .env)

# USER SERVICE_USER_FASTQ
service_user_fastq_key_name = utils.load_check_env_var('SERVICE_USER_FASTQ_RW_SECRET_KEY_NAME')

if service_user_fastq_key_name:
    print(f"Loading service user fastq key from AWS Secrets Manager: {service_user_fastq_key_name}")
    service_user_fastq_key_json = aws_secrets_manager.get_secret_value_json(service_user_fastq_key_name)
    service_user_fastq_pwd = service_user_fastq_key_json['password']
    service_user_fastq_name = service_user_fastq_key_json['username']
else:
    service_user_fastq_pwd = utils.load_check_env_var('SERVICE_USER_FASTQ_RW_PWD')
    service_user_fastq_name = utils.load_check_env_var('SERVICE_USER_FASTQ_RW')

password = make_password(service_user_fastq_pwd)

# Create Service Users
if not User.objects.filter(username=service_user_fastq_name).exists():
    service_user_rw = User.objects.create(
        username=service_user_fastq_name,
        password=password)
    service_user_rw.groups.set([service_group_rw])
else:
    service_user_rw = User.objects.get(username=service_user_fastq_name)

# USER SERVICE_USER_HEALTHCHECK
service_user_healthcheck_key_name = utils.load_check_env_var('SERVICE_USER_HEALTHCHECK_SECRET_KEY_NAME')

if service_user_healthcheck_key_name:
    print(f"Loading service user fastq key from AWS Secrets Manager: {service_user_healthcheck_key_name}")
    service_user_healthcheck_key_json = aws_secrets_manager.get_secret_value_json(service_user_healthcheck_key_name)
    service_user_healthcheck_pwd = service_user_healthcheck_key_json['password']
    service_user_healthcheck_name = service_user_healthcheck_key_json['username']
else:
    print("Loading service user fastq key from .env")
    service_user_healthcheck_name = utils.load_check_env_var('SERVICE_USER_HEALTHCHECK')
    service_user_healthcheck_pwd = utils.load_check_env_var('SERVICE_USER_HEALTHCHECK_PWD')    

password = make_password(service_user_healthcheck_pwd)

# Create Service Users

if not User.objects.filter(username=service_user_healthcheck_name).exists():
    service_user_healthcheck = User.objects.create(
        username=service_user_healthcheck_name,
        password=password)
    service_user_healthcheck.groups.set([service_group_r])
else:
    service_user_healthcheck = User.objects.get(username=service_user_healthcheck_name)

# USER SERVICE_USER_APP

service_user_appuser_key_name = utils.load_check_env_var('SERVICE_USER_APPUSER_SECRET_KEY_NAME')

if service_user_appuser_key_name:
    print(f"Loading service app user key from AWS Secrets Manager: {service_user_appuser_key_name}")
    service_user_appuser_key_json = aws_secrets_manager.get_secret_value_json(service_user_appuser_key_name)
    service_user_appuser_pwd = service_user_appuser_key_json['password']
    service_user_appuser_name = service_user_appuser_key_json['username']
else:
    print("Loading service user fastq key from .env")
    service_user_appuser_name = utils.load_check_env_var('SERVICE_USER_APPUSER')
    service_user_appuser_pwd = utils.load_check_env_var('SERVICE_USER_APPUSER_PWD')    

password = make_password(service_user_appuser_pwd)

# Create Service Users
if not User.objects.filter(username=service_user_appuser_name).exists():
    service_user_appuser = User.objects.create(
        username=service_user_appuser_name,
        password=password)
    service_user_appuser.groups.set([app_user_group])
else:
    service_user_appuser = User.objects.get(username=service_user_appuser_name)

print("DONE.")
