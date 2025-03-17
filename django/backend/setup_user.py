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
from scrnaseq.models import FastqDatasets
from scrnaseq.models import ScrnaseqDatasets
from scrnaseq.models import ScrnaseqIntegration


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
                                  view_scrnaseq_integration,
                                  view_scrnaseq_dataset_annotations,
                                  view_scrnaseq_cluster_annotations])

service_group_rw.permissions.set([add_fastqdatasets, change_fastqdatasets, view_fastqdatasets,
                                  add_scrnaseq_dataset, change_scrnaseq_dataset, view_scrnaseq_dataset,
                                  add_scrnaseq_integration, change_scrnaseq_integration, view_scrnaseq_integration,
                                  add_scrnaseq_dataset_annotations, change_scrnaseq_dataset_annotations, view_scrnaseq_dataset_annotations,
                                  add_scrnaseq_cluster_annotations, change_scrnaseq_cluster_annotations, view_scrnaseq_cluster_annotations])

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

# # Load database logins from AWS Secrets Manager (or .env)
aws_secrets_manager = aws.AwsSecretsManager()

# USER: SERVICE_USER_FASTQ
service_user_fastq_key_name = utils.load_check_env_var('SERVICE_USER_FASTQ_RW_SECRET_KEY_NAME')

if service_user_fastq_key_name:
    print(f"Loading service user fastq key from AWS Secrets Manager: {service_user_fastq_key_name}")
    service_user_fastq_key_json = aws_secrets_manager.get_secret_value_json(service_user_fastq_key_name)
    service_user_fastq_pwd = service_user_fastq_key_json['password']
    service_user_fastq_name = service_user_fastq_key_json['username']
else:
    print("Loading service user fastq key from .env")
    service_user_fastq_name = utils.load_check_env_var('SERVICE_USER_FASTQ_RW')
    service_user_fastq_pwd = utils.load_check_env_var('SERVICE_USER_FASTQ_RW_PWD')    

password = make_password(service_user_fastq_pwd)

# Create Service Users
if not User.objects.filter(username=service_user_fastq_name).exists():
    service_user_rw = User.objects.create(
        username=service_user_fastq_name,
        password=password)
    service_user_rw.groups.set([service_group_rw])
else:
    service_user_rw = User.objects.get(username=service_user_fastq_name)

# USER: SERVICE_USER_HEALTHCHECK
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
        username=service_user_fastq_name,
        password=password)
    service_user_healthcheck.groups.set([service_group_r])
else:
    service_user_healthcheck = User.objects.get(username=service_user_healthcheck_name)

# USER SERVICE_USER_APP

service_user_appuser_key_name = utils.load_check_env_var('SERVICE_USER_APPUSER_SECRET_KEY_NAME')

if service_user_appuser_key_name:
    print(f"Loading service user fastq key from AWS Secrets Manager: {service_user_appuser_key_name}")
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

# Add test datasets

print("Add test datasets....")

# Load test datases from S3
# Large fastq dataset
fq_ds, created = FastqDatasets.objects.get_or_create(name='fq_Chromium_3p_GEX_Human_PBMC_S1_L001_jZZLTLBsS0OI-nOgvKyK3A',
                                    s3_bucket='al-case-scrnaseq-data',
                                    s3_source_key='Chromium_3p_GEX_Human_PBMC_fastqs.tar',
                                    s3_source_bucket='al-case-scrnaseq-upload',
                                    s3_read1_fastq_key='fastq_dataset/20240620/fq_Chromium_3p_GEX_Human_PBMC_S1_L001_jZZLTLBsS0OI-nOgvKyK3A_S1_R1_001.fastq.gz',
                                    s3_read2_fastq_key='fastq_dataset/20240620/fq_Chromium_3p_GEX_Human_PBMC_S1_L001_jZZLTLBsS0OI-nOgvKyK3A_S1_R2_001.fastq.gz',
                                    owner=service_user_rw)

fq_ds1, created = FastqDatasets.objects.get_or_create(name='fq_Chromium_3p_GEX_Human_PBMC_S1_L001_QJzjQmL1R6-8uaqRa_y_tw',
                                    s3_bucket='al-case-scrnaseq-data',
                                    s3_source_key='Chromium_3p_GEX_Human_PBMC_fastqs_1M.tar',
                                    s3_source_bucket='al-case-scrnaseq-upload',
                                    s3_read1_fastq_key='fastq_dataset/20240620/fq_Chromium_3p_GEX_Human_PBMC_S1_L001_QJzjQmL1R6-8uaqRa_y_tw_S1_R1_001.fastq.gz',
                                    s3_read2_fastq_key='fastq_dataset/20240620/fq_Chromium_3p_GEX_Human_PBMC_S1_L001_QJzjQmL1R6-8uaqRa_y_tw_S1_R2_001.fastq.gz',
                                    owner=service_user_rw)

fq_ds2, created = FastqDatasets.objects.get_or_create(name='fq_Chromium_3p_GEX_Human_PBMC_S1_L001_9upLsAaqT8Cxtj2lo0kvKA',
                                    s3_bucket='al-case-scrnaseq-data',
                                    s3_source_key='Chromium_3p_GEX_Human_PBMC_fastqs_10M.tar',
                                    s3_source_bucket='al-case-scrnaseq-upload',
                                    s3_read1_fastq_key='fastq_dataset/20240702/fq_Chromium_3p_GEX_Human_PBMC_S1_L001_9upLsAaqT8Cxtj2lo0kvKA_S1_R1_001.fastq.gz',
                                    s3_read2_fastq_key='fastq_dataset/20240702/fq_Chromium_3p_GEX_Human_PBMC_S1_L001_9upLsAaqT8Cxtj2lo0kvKA_S1_R2_001.fastq.gz',
                                    owner=service_user_rw)

sc_ds1, created = ScrnaseqDatasets.objects.get_or_create(name='sc_Chromium_3p_GEX_Human_PBMC_S1_L001_xKFRG5TxQSeorSwPriTbAQ1',
                                       fastq_dataset = fq_ds,
                                        transcriptome='mytransc',
                                        s3_bucket='al-case-scrnaseq-data',
                                        s3_qc_metrics_key='scrnaseq_dataset/sc_Chromium_3p_GEX_Human_PBMC_S1_L001GELyPBYIRxOIXnwDIkQVNg/qc_metrics.csv',
                                        s3_gene_expression_matrix_key = 'scrnaseq_dataset/sc_Chromium_3p_GEX_Human_PBMC_S1_L001GELyPBYIRxOIXnwDIkQVNg/dge.h5',
                                        s3_gene_expression_matrix_size_mb = 21,
                                        number_cells = 5141,
                                        mean_reads_per_cell = 35466,
                                        median_number_genes_per_cell = 2870,
                                        total_number_reads = 182330834,
                                        pipeline_version = 'v0.1.0',
                                        owner=service_user_rw)

sc_ds2, created = ScrnaseqDatasets.objects.get_or_create(name='sc_Chromium_3p_GEX_Human_PBMC_S1_L001_xKFRG5TxQSeorSwPriTbAQ2',
                                       fastq_dataset = fq_ds1,
                                        transcriptome='mytransc',
                                        s3_bucket='al-case-scrnaseq-data',
                                        s3_qc_metrics_key='scrnaseq_dataset/sc_Chromium_3p_GEX_Human_PBMC_S1_L001_QJzjQmL1R6-8uaqRa_ypNfhNc/qc_metrics.csv',
                                        s3_gene_expression_matrix_key = 'scrnaseq_dataset/sc_Chromium_3p_GEX_Human_PBMC_S1_L001_QJzjQmL1R6-8uaqRa_ypNfhNc/dge.h5',
                                        s3_gene_expression_matrix_size_mb=4.0,
                                        number_cells = 4811,
                                        mean_reads_per_cell = 2079,
                                        median_number_genes_per_cell = 647,
                                        total_number_reads = 10000000,
                                        pipeline_version = 'v0.1.0',
                                        owner=service_user_rw)

sc_int_1, created = ScrnaseqIntegration.objects.get_or_create(name='sc_int_1',
                                                    min_genes_per_cell = 300,
                                                    min_cells_per_gene = 300,
                                                    num_highly_variable_genes = 2000,
                                                    num_pcs = 50,
                                                    leiden_resolution = 1.0,
                                                    s3_bucket = 'al-case-scrnaseq-data',
                                                    s3_adata_key = 'scrnaseq_integration/integration_20240621_ZK5o5PodQPC2EHU4cNMRaA/adata.h5ad',
                                                    s3_umap_key = 'scrnaseq_integration/integration_20240621_ZK5o5PodQPC2EHU4cNMRaA/umap.csv',
                                                    s3_adata_obs_key = 'scrnaseq_integration/integration_20240621_ZK5o5PodQPC2EHU4cNMRaA/adata_obs.csv',
                                                    pipeline_version = 'v0.1.0',
                                                    owner=service_user_rw)
                                                     
sc_ds1.scrnaseq_integration.add(sc_int_1)
sc_ds2.scrnaseq_integration.add(sc_int_1)

sc_int_1.scrnaseq_dataset.set([sc_ds1, sc_ds2])
                                              
print("DONE.")
