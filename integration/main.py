# case-scrnaseq/integration/main.py

import argparse
import tempfile
import os
import subprocess
import datetime
import sys
from typing import List

import requests
from requests.auth import HTTPBasicAuth
import pandas as pd
from pydantic import BaseModel
from dotenv import load_dotenv
import scanpy as sc
import anndata as ad

from zihelper import aws
from zihelper import utils
from zihelper import exceptions as ziexceptions

from __version__ import __version__

__author__ = "Jonathan Alles"
__email__ = "Jonathan.Alles@evo-byte.com"
__copyright__ = "Copyright 2024"

load_dotenv()

# Constants and environment variables
SERVICE_USER_SECRET_KEY_NAME = utils.load_check_env_var('INTEGRATION_SERVICE_USER_SECRET_KEY_NAME')
SERVICE_USER=utils.load_check_env_var('INTEGRATION_SERVICE_USER')
SERVICE_USER_PWD=utils.load_check_env_var('INTEGRATION_SERVICE_USER_PWD')

SCRNASEQ_DATASETS_BACKEND_URL = utils.load_check_env_var('SCRNASEQ_DATASETS_BACKEND_URL').rstrip('/') # Remove trailing slash for format list URL
SCRNASEQ_INTEGRATION_BACKEND_URL = utils.load_check_env_var('SCRNASEQ_INTEGRATION_BACKEND_URL').rstrip('/') # Remove trailing slash for format list URL

OUTPUT_S3_BUCKET = utils.load_check_env_var('INTEGRATION_OUTPUT_S3_BUCKET')
OUTPUT_S3_KEY_PREFIX = utils.load_check_env_var('INTEGRATION_OUTPUT_S3_KEY_PREFIX')

MAX_RAM_GB = utils.load_check_env_var('INTEGRATION_MAX_RAM_GB') # Define max RAM for loading data
MIN_GENES_PER_CELL = utils.load_check_env_var('INTEGRATION_MIN_GENES_PER_CELL') # Define min genes per cell for filtering
MIN_CELLS_PER_GENE = utils.load_check_env_var('INTEGRATION_MIN_CELLS_PER_GENE') # Define min cells per gene for filtering
NUM_HIGHLY_VARIABLE_GENES = utils.load_check_env_var('INTEGRATION_NUM_HIGHLY_VARIABLE_GENES') # Define number of highly variable genes for PCA
LEIDEN_RESOLUTION = utils.load_check_env_var('INTEGRATION_LEIDEN_RESOLUTION') # Define resolution for leiden clustering 
NUM_PCA = utils.load_check_env_var('INTEGRATION_NUM_PCA') # Define resolution for leiden clustering 

# Cast data types
MAX_RAM_GB = int(MAX_RAM_GB)
MIN_GENES_PER_CELL = int(MIN_GENES_PER_CELL)
MIN_CELLS_PER_GENE = int(MIN_CELLS_PER_GENE)
INTEGRATION_NUM_HIGHLY_VARIABLE_GENES = int(NUM_HIGHLY_VARIABLE_GENES)
LEIDEN_RESOLUTION = float(LEIDEN_RESOLUTION)
NUM_PCA = int(NUM_PCA)

# PARSER

# DATA CLASSES

class ScrnaseqDatasets(BaseModel):
    id: int
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
    valid_from : datetime.datetime
    valid_to : datetime.datetime | None

class ScrnaseqDatasetsIntegration(BaseModel):
    name: str
    scrnaseq_dataset: List[int]
    min_genes_per_cell: int
    min_cells_per_gene: int
    num_highly_variable_genes: int
    num_pcs: int
    leiden_resolution: float
    s3_bucket: str
    s3_adata_key: str
    s3_umap_key: str
    s3_adata_obs_key: str
    pipeline_version: str

# METHODS

# MAIN

def main():
    
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

    # CHECK: Connection to backend scrnaseq_datasets
    print(f'Test connection to backend URL {SCRNASEQ_DATASETS_BACKEND_URL}')

    res = requests.get(SCRNASEQ_DATASETS_BACKEND_URL, auth=login)
    assert res.status_code == 200, f'Backend URL {SCRNASEQ_DATASETS_BACKEND_URL} is not reachable. Exit.'
    
    # CHECK: Connection to backend scrnaseq_integration
    print(f'Test connection to backend URL {SCRNASEQ_INTEGRATION_BACKEND_URL}')

    res = requests.get(SCRNASEQ_INTEGRATION_BACKEND_URL, auth=login)
    assert res.status_code == 200, f'Backend URL {SCRNASEQ_INTEGRATION_BACKEND_URL} is not reachable. Exit.'
    
    # LOAD: dge files datasets
    print("Download dge.h5 from S3")
    
    # Get fastq S3 keys from backend
    res = requests.get(f"{SCRNASEQ_DATASETS_BACKEND_URL}/get_valid", auth=login)
    assert res.status_code == 200, f'Failed to get fastq datasets. Exit.'
    
    scrnaseq_datasets = [
        ScrnaseqDatasets(**dataset) for dataset in res.json()
    ]
    
    total_dge_size_mb = sum([dataset.s3_gene_expression_matrix_size_mb for dataset in scrnaseq_datasets])
    total_dge_size_gb = round(total_dge_size_mb / 1024,2)
    expected_ram_size = round(total_dge_size_gb * 8,2)
    
    print(f"Total DGE size: {total_dge_size_gb} GB")
    print(f"Expected AnnData size: {expected_ram_size} GB")
    
    # Expected 8-fold size of RAM ann data object comapre to h5ad compressed
    
    assert total_dge_size_mb <= (MAX_RAM_GB * 1024), f"Total DGE size(s) exceeds max RAM. Exit."

    # Create a temporary folder and download the fastq files
    temp_dir = tempfile.TemporaryDirectory(delete=False)
    
    # Move to temp dir
    os.chdir(temp_dir.name)
    
    h5_dir = os.path.join(temp_dir.name, 'input_h5')
    os.makedirs(h5_dir, exist_ok=True)
    
    print("Download DGEs")
    
    dge_paths = []
    for dataset in scrnaseq_datasets:
        dataset_name = dataset.name
        h5_path = os.path.join(h5_dir, dataset_name + '_dge.h5')
        
        aws_s3.download_key_from_bucket(dataset.s3_bucket, dataset.s3_gene_expression_matrix_key, h5_path)
        dge_paths.append(h5_path)
    
    # LOAD: data into scanpy and concat
    adatas = {}
    for dge_p in dge_paths:
        dataset_name = os.path.basename(dge_p).replace('_dge.h5', '')
        adata = sc.read_10x_h5(dge_p)
        adata.var_names_make_unique()
        adatas[dataset_name] = adata
        
    # Concatenate datasets
    adata_concat = ad.concat(adatas, label="sample")
    adata_concat.obs_names_make_unique()
    
    # CALC: QC Metrics

    print("Calculate QC metrics and filter")
    
    # mitochondrial genes, "MT-" for human, "Mt-" for mouse
    adata_concat.var["mt"] = adata_concat.var_names.str.startswith("MT-")
    # ribosomal genes
    adata_concat.var["ribo"] = adata_concat.var_names.str.startswith(("RPS", "RPL"))
    # hemoglobin genes
    adata_concat.var["hb"] = adata_concat.var_names.str.contains("^HB[^(P)]")

    sc.pp.calculate_qc_metrics(
        adata_concat, qc_vars=["mt", "ribo", "hb"], inplace=True, log1p=True
    )
    
    # CALC: Filter
    sc.pp.filter_cells(adata_concat, min_genes=MIN_GENES_PER_CELL)
    sc.pp.filter_genes(adata_concat, min_cells=MIN_CELLS_PER_GENE)
    
    # CALC DUBLET REMOVAL    
    sc.pp.scrublet(adata_concat, batch_key="sample")
    adata_concat = adata_concat[adata_concat.obs['predicted_doublet'] == False, :]

    # CALC: Norm and scale
    adata_concat.layers["counts"] = adata_concat.X.copy()
    
    print("Normalize data")
    
    # Normalizing to median total counts
    sc.pp.normalize_total(adata_concat)
    # Logarithmize the data
    sc.pp.log1p(adata_concat)
    
    print("Identify highly variable genes")

    # CALC: Highly variable genes and PCA
    sc.pp.highly_variable_genes(adata_concat,
                                n_top_genes=INTEGRATION_NUM_HIGHLY_VARIABLE_GENES,
                                batch_key="sample")

    print("Run PCA")
    
    # PCA, by default only calculated for highly variable genes
    sc.tl.pca(adata_concat, n_comps=NUM_PCA)

    print("Get Neighbors and UMAP")

    sc.pp.neighbors(adata_concat)

    # UMAP
    sc.tl.umap(adata_concat)

    print("Run Leiden clustering")
    
    # CALC: Clustering
    sc.tl.leiden(adata_concat, resolution=LEIDEN_RESOLUTION)
    
    # Define output vectors
    adata_concat_obs = adata_concat.obs
    
    # Extract UMAP coordinates
    umap_coords = adata_concat.obsm['X_umap'] # numpy array
    umap_coords_df = pd.DataFrame(umap_coords, columns=['umap1', 'umap2'])
    
    # Write to h5ad
    adata_p = os.path.join(temp_dir.name, 'adata.h5ad')
    adata_obs_p = os.path.join(temp_dir.name, 'adata_obs.csv')
    umap_p = os.path.join(temp_dir.name, 'umap.csv')
    
    adata_concat.write(adata_p)
    adata_concat_obs.to_csv(adata_obs_p)
    umap_coords_df.to_csv(umap_p)
    
    uuid_short = utils.generate_short_uuid()
    date = datetime.datetime.now().strftime('%Y%m%d')
    
    sc_dataset_name = 'integration_' + date + '_' + uuid_short
    
    # Output S3 keys
    adata_key = os.path.join(OUTPUT_S3_KEY_PREFIX, sc_dataset_name, 'adata.h5ad')
    adata_obs_key = os.path.join(OUTPUT_S3_KEY_PREFIX, sc_dataset_name, 'adata_obs.csv')
    umap_key = os.path.join(OUTPUT_S3_KEY_PREFIX, sc_dataset_name, 'umap.csv')
    
    print('Upload to S3')
    
    # Upload to S3
    aws_s3.upload_file_to_bucket(OUTPUT_S3_BUCKET, adata_key, adata_p)
    aws_s3.upload_file_to_bucket(OUTPUT_S3_BUCKET, adata_obs_key, adata_obs_p)
    aws_s3.upload_file_to_bucket(OUTPUT_S3_BUCKET, umap_key, umap_p)
        
    scrnaseq_integration = ScrnaseqDatasetsIntegration(
        name=sc_dataset_name,
        scrnaseq_dataset=[dataset.id for dataset in scrnaseq_datasets],
        min_genes_per_cell=MIN_GENES_PER_CELL,
        min_cells_per_gene=MIN_CELLS_PER_GENE,
        num_highly_variable_genes=INTEGRATION_NUM_HIGHLY_VARIABLE_GENES,
        num_pcs=NUM_PCA,
        leiden_resolution=LEIDEN_RESOLUTION,
        s3_bucket=OUTPUT_S3_BUCKET,
        s3_adata_key=adata_key,
        s3_umap_key=umap_key,
        s3_adata_obs_key=adata_obs_key,
        pipeline_version=__version__
    )
    
    print('POST dataset json.')
    res = requests.post(SCRNASEQ_INTEGRATION_BACKEND_URL + '/', auth=login, data=scrnaseq_integration.model_dump())
    assert res.status_code == 201, f'POST request failed with status code {res.status_code}. Exit.'

    temp_dir.cleanup()
    
    os.chdir(init_wd)
    
if __name__ == '__main__':
    
    print('Integration started. Exit.')
        
    main()
    
    print('Integration completed. Exit.')