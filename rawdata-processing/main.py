# case-scrnaseq/rawdata-processing/main.py

import argparse
import tempfile
import os
import subprocess
import datetime

import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from pydantic import BaseModel
from dotenv import load_dotenv

from zihelper import aws
from zihelper import utils
from zihelper import exceptions as ziexceptions

from __version__ import __version__

__author__ = "Jonathan Alles"
__email__ = "Jonathan.Alles@evo-byte.com"
__copyright__ = "Copyright 2024"

load_dotenv()

# Constants and environment variables
SERVICE_USER_SECRET_KEY_NAME = utils.load_check_env_var('RAWDATA_PROCESSING_SERVICE_USER_SECRET_KEY_NAME')
SERVICE_USER=utils.load_check_env_var('RAWDATA_PROCESSING_SERVICE_USER')
SERVICE_USER_PWD=utils.load_check_env_var('RAWDATA_PROCESSING_SERVICE_USER_PWD')

FASTQ_REGISTRATION_BACKEND_URL = utils.load_check_env_var('FASTQ_REGISTRATION_BACKEND_URL').rstrip('/') # Remove trailing slash for format list URL
RAWDATA_PROCESSING_BACKEND_URL = utils.load_check_env_var('RAWDATA_PROCESSING_BACKEND_URL').rstrip('/') # Remove trailing slash for format list URL

RAWDATA_PROCESSING_GENOME_S3_KEY = utils.load_check_env_var('RAWDATA_PROCESSING_GENOME_S3_KEY')
RAWDATA_PROCESSING_GENOME_S3_BUCKET = utils.load_check_env_var('RAWDATA_PROCESSING_GENOME_S3_BUCKET')

RAWDATA_PROCESSING_NUM_CORES = int(utils.load_check_env_var('RAWDATA_PROCESSING_NUM_CORES'))
RAWDATA_PROCESSING_MEM_GB = int(utils.load_check_env_var('RAWDATA_PROCESSING_MEM_GB'))

# PARSER

parser = argparse.ArgumentParser()
parser.add_argument(
    "--s3-input-key", 
    dest='s3_input_key',
    required=True,
    type=str,
    help="Input dataset directory"
)

parser.add_argument(
    "--s3-bucket",
    dest='s3_bucket',
    required=True,
    type=str,
    help="S3 bucket name"
)

# DATA CLASSES

class FastqDatasets(BaseModel):
    id: int
    name: str
    s3_bucket : str
    s3_source_key : str
    s3_source_bucket : str
    s3_read1_fastq_key : str
    s3_read2_fastq_key : str

class ScrnaseqDatasets(BaseModel):
    name: str
    fastq_dataset : int
    transcriptome : str
    s3_bucket : str
    s3_qc_metrics_key : str
    s3_gene_expression_matrix_key : str
    s3_gene_expression_matrix_size_mb : float
    number_cells : int
    mean_reads_per_cell : int
    median_number_genes_per_cell : int
    total_number_reads : int
    pipeline_version : str
    
# METHODS

# MAIN

def main(s3_input_key: str, s3_bucket: str):
    
    aws_s3 = aws.AwsS3()
    init_wd = os.getcwd()
    
    # CHECK: backend credentials can be defined
    if SERVICE_USER_SECRET_KEY_NAME:
        aws_secrets_manager = aws.AwsSecretsManager()
        secret_key_json = aws_secrets_manager.get_secret_value_json(SERVICE_USER_SECRET_KEY_NAME)
        service_user_name = secret_key_json['username']
        service_user_pwd = secret_key_json['password']    
    else:
        service_user_pwd = SERVICE_USER_PWD
        service_user_name = SERVICE_USER
    login = HTTPBasicAuth(service_user_name, service_user_pwd)

    # CHECK: Connection to backend fastq_datasets
    print(f'Test connection to backend URL {FASTQ_REGISTRATION_BACKEND_URL}')

    res = requests.get(FASTQ_REGISTRATION_BACKEND_URL, auth=login)
    assert res.status_code == 200, f'Backend URL {FASTQ_REGISTRATION_BACKEND_URL} is not reachable. Exit.'
    
    # CHECK: Connection to rawdata processing
    print(f'Test connection to backend URL {RAWDATA_PROCESSING_BACKEND_URL}')
    
    res = requests.get(RAWDATA_PROCESSING_BACKEND_URL, auth=login)
    assert res.status_code == 200, f'Backend URL {RAWDATA_PROCESSING_BACKEND_URL} is not reachable. Exit.'
    
    # LOAD: Fastq datasets
    print("Download fastq files from S3")
    
    # Get fastq S3 keys from backend
    params = {'s3_read2_fastq_key': s3_input_key}
    res = requests.get(f"{FASTQ_REGISTRATION_BACKEND_URL}/get_by_s3_read2_fastq_key", params=params, auth=login)
    assert res.status_code == 200, f'Failed to get fastq datasets. Exit.'
    
    # Read in data class
    fastq_dataset = FastqDatasets(**res.json())
    
    # Define new dataset name from fastq dataset name
    # fq_dataset_name example: fq_Chromium_3p_GEX_Human_PBMC_S1_L001_xKFRG5TxQSeorSwPriTbAQ
    # Strip fq_ prefix and uuid suffix and add new uuid suffix
    uuid_short = utils.generate_short_uuid()
    sc_dataset_name = 'sc_' + '_'.join(fastq_dataset.name.lstrip('fq_').split('_')[:-1])
    sc_dataset_name += uuid_short
    
    # Ensure that the dataset name is max 63 characters long
    if len(sc_dataset_name) > 63:
        print("WARNING: Dataset name is longer than 63 characters. Truncating to 63 characters.")
        sc_dataset_name = sc_dataset_name[:63]
    
    # Create a temporary folder and download the fastq files
    temp_dir = tempfile.TemporaryDirectory(delete=True)
    
    # Move to temp dir
    os.chdir(temp_dir.name)
    
    fq_dir = os.path.join(temp_dir.name, fastq_dataset.name)
    os.makedirs(fq_dir, exist_ok=True)
    
    read1_path = os.path.join(fq_dir, os.path.basename(fastq_dataset.s3_read1_fastq_key))
    read2_path = os.path.join(fq_dir, os.path.basename(fastq_dataset.s3_read2_fastq_key))
    
    aws_s3.download_key_from_bucket(s3_bucket, fastq_dataset.s3_read1_fastq_key, read1_path)
    aws_s3.download_key_from_bucket(s3_bucket, fastq_dataset.s3_read2_fastq_key, read2_path)
    
    # LOAD: Genome reference
    print(f"""Download transcriptome reference from S3 bucket {RAWDATA_PROCESSING_GENOME_S3_BUCKET} and key {RAWDATA_PROCESSING_GENOME_S3_KEY}""")
    
    tx_name = os.path.basename(RAWDATA_PROCESSING_GENOME_S3_KEY)
    aws_s3.download_folder_from_bucket(RAWDATA_PROCESSING_GENOME_S3_BUCKET, RAWDATA_PROCESSING_GENOME_S3_KEY, tx_name)
    
    print(f'Start alignment for scRNA-seq dataset {sc_dataset_name}')
    
    cellranger_cmd = [
        'cellranger',
        'count',
        f'--id={sc_dataset_name}',
        f'--transcriptome={tx_name}',
        '--fastqs=' + fq_dir,
        '--sample=' + fastq_dataset.name,
        '--create-bam=false',
        f'--localcores={RAWDATA_PROCESSING_NUM_CORES}',
        f'--localmem={RAWDATA_PROCESSING_MEM_GB}',
        '--nosecondary'
    ]
    
    # EXEC: Cellranger Pipeline
    subprocess.call(cellranger_cmd)
    
    # Collect and parse output files
    sc_dataset_outdir = os.path.join(temp_dir.name, sc_dataset_name, 'outs')
    
    metrics_summary = os.path.join(sc_dataset_outdir, 'metrics_summary.csv')
    filtered_feat_bc_matrix = os.path.join(sc_dataset_outdir, 'filtered_feature_bc_matrix.h5')
    
    assert os.path.exists(metrics_summary), f'Cellranger failed to generate metrics_summary.csv. Exit.'
    assert os.path.exists(filtered_feat_bc_matrix), f'Cellranger failed to generate filtered_feature_bc_matrix.h5. Exit.'
    
    # Returns size in bytes
    feat_bc_matrix_size_mb = round(os.path.getsize(filtered_feat_bc_matrix) / (1024*1024),2)
    
    # Parse metrics and cast datatypes
    metrics = pd.read_csv(metrics_summary, thousands=',')
    metrics['Estimated Number of Cells'] = metrics['Estimated Number of Cells'].astype(int)
    metrics['Mean Reads per Cell'] = metrics['Mean Reads per Cell'].astype(int)
    metrics['Median Genes per Cell'] = metrics['Median Genes per Cell'].astype(int)
    metrics['Number of Reads'] = metrics['Number of Reads'].astype(int)
    
    # Perform data upload
    s3_qc_metrics_key = os.path.join('scrnaseq_dataset', sc_dataset_name, 'qc_metrics.csv')
    s3_gene_expression_matrix_key = os.path.join('scrnaseq_dataset', sc_dataset_name, 'dge.h5')
    
    print(f'Upload files to S3 bucket {s3_bucket}')
    
    aws_s3.upload_file_to_bucket(s3_bucket, s3_qc_metrics_key, metrics_summary)
    aws_s3.upload_file_to_bucket(s3_bucket, s3_gene_expression_matrix_key, filtered_feat_bc_matrix)
    # Make pydantic way
    scrnaseq_dataset = ScrnaseqDatasets(
        name=sc_dataset_name,
        fastq_dataset=str(fastq_dataset.id),
        transcriptome=tx_name,
        s3_bucket=s3_bucket,
        s3_qc_metrics_key=s3_qc_metrics_key,
        s3_gene_expression_matrix_key=s3_gene_expression_matrix_key,
        s3_gene_expression_matrix_size_mb=feat_bc_matrix_size_mb,
        number_cells=metrics['Estimated Number of Cells'].values[0],
        mean_reads_per_cell=metrics['Mean Reads per Cell'].values[0],
        median_number_genes_per_cell=metrics['Median Genes per Cell'].values[0],
        total_number_reads=metrics['Number of Reads'].values[0],
        pipeline_version=__version__
    )
        
    print('POST dataset json.')
    res = requests.post(RAWDATA_PROCESSING_BACKEND_URL + '/', auth=login, data=scrnaseq_dataset.model_dump())
    assert res.status_code == 201, f'POST request failed with status code {res.status_code}. Exit.'

    temp_dir.cleanup()
    
    os.chdir(init_wd)
    
if __name__ == '__main__':
    
    args = parser.parse_args()
    s3_input_key = args.s3_input_key
    s3_bucket = args.s3_bucket

    main(s3_input_key, s3_bucket)
    
    print('rawdata-processing completed. Exit.')