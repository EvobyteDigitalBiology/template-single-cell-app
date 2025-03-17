import streamlit as st
import pandas as pd
import requests
from pydantic import BaseModel
import numpy as np
import natsort

from zihelper import aws

# Cached funtions to S3 data to disk
import uiconfig
import exceptions

from uidataclasses import ScrnaseqDatasets
from uidataclasses import ScrnaseqDatasetAnnotations
from uidataclasses import ScrnaseqDatasetsIntegration
from uidataclasses import ScrnaseqClusterAnnotations


assert 'httpauth' in st.session_state, "httpauth not in session state"

def get_request_to_dataframe(http_endpoint: str, auth: requests.auth.HTTPBasicAuth, validation_class: BaseModel) -> pd.DataFrame:
    
    # HTTP Request
    res = requests.get(http_endpoint, auth=auth)
    res_json = res.json()
    # data validation, returned json must be a list
    assert res.status_code == 200, f"Error: {res.status_code}"
    assert isinstance(res_json, list), "Returned data is not a list"
    
    # Data validation using pydantic
    data = [validation_class(**ele) for ele in res_json]
    
    # Empty list case: get dataframe with empty columns based on pydantic model
    # or cast validated data to dataframe
    if data == []:
        df = pd.DataFrame(columns=validation_class.__fields__.keys())
    else:
        df = pd.DataFrame([ele.dict() for ele in data])
    
    return df

@st.cache_data(persist=True)
def download_df_from_s3(s3_bucket: str, s3_key: str) -> pd.DataFrame:
    
    aws_s3 = aws.AwsS3()
    
    # Download data from S3 bucket
    df = pd.read_csv(f"s3://{s3_bucket}/{s3_key}")
    
    return df

# Functions to load integrations / scrnaseq datasets from django backend
@st.cache_data
def get_valid_scrnaseq_datasets() -> pd.DataFrame:
    
    endpoint = f"{uiconfig.BACKEND_API_ENDPOINT}/scrnaseq_datasets/get_valid/"
    auth = st.session_state['httpauth']
    df = get_request_to_dataframe(endpoint, auth, ScrnaseqDatasets)
    
    return df

@st.cache_data
def get_valid_scrnaseq_integration() -> pd.DataFrame:
    
    endpoint = f"{uiconfig.BACKEND_API_ENDPOINT}/scrnaseq_integration/get_valid/"
    auth = st.session_state['httpauth']
    df = get_request_to_dataframe(endpoint, auth, ScrnaseqDatasetsIntegration)
    
    return df

@st.cache_data
def get_valid_scrnaseq_dataset_annotations() -> pd.DataFrame:
    
    endpoint = f"{uiconfig.BACKEND_API_ENDPOINT}/scrnaseq_dataset_annotations/get_valid/"
    auth = st.session_state['httpauth']
    df = get_request_to_dataframe(endpoint, auth, ScrnaseqDatasetAnnotations)
    
    # Reformat columns related to annotation, since json stored in annotation JSON in DB
    # will be reformat. If Df is empty, add name_alias and descrition default columns to display
    if df.empty:
        df = df.drop(columns=['annotation'])
        df['annotation_name_alias'] = None
        df['annotation_description'] = None
    else:
        # Case json stored in annotation columns in wide format for display
        annotations = df['annotation'].values
        annotations_df = pd.DataFrame(annotations.tolist())
        annotations_df = annotations_df.add_prefix('annotation_')
        
        if not 'annotation_name_alias' in annotations_df.columns:
            annotations_df['annotation_name_alias'] = None
        if not 'annotation_description' in annotations_df.columns:
            annotations_df['annotation_description'] = None
        
        df = df.drop(columns=['annotation'])
        df = pd.concat([df, annotations_df], axis=1)
                  
    return df

@st.cache_data
def get_valid_scrnaseq_cluster_annotations() -> pd.DataFrame:
    
    endpoint = f"{uiconfig.BACKEND_API_ENDPOINT}/scrnaseq_cluster_annotations/get_valid/"
    auth = st.session_state['httpauth']
    df = get_request_to_dataframe(endpoint, auth, ScrnaseqClusterAnnotations)
    
    return df

@st.cache_data
def load_scrnaseq_dataset_annotations() -> pd.DataFrame:
    
    # Get valid datasets from server and combine with available annotations
    # Merge datasets into valid scrnaseq datasets and remove UUIDs from names
    scrnaseq_datasets = get_valid_scrnaseq_datasets() # Could come from session state
    scrnaseq_dataset_annotations = get_valid_scrnaseq_dataset_annotations() # Could come from session state
    
    scrnaseq_df_merged = pd.merge(scrnaseq_datasets,
                                   scrnaseq_dataset_annotations,
                                   how='left',
                                   left_on='id',
                                   right_on='scrnaseq_dataset')
    
    # Replace NaNs with None
    scrnaseq_df_merged = scrnaseq_df_merged.replace(np.nan, None)
        
    # Get columns containing annotations, e.g. name_alias, description, remove trailing annotations to display
    annotations_df = scrnaseq_df_merged.loc[:,scrnaseq_df_merged.columns.str.startswith('annotation_')]
    annotations_df.columns = annotations_df.columns.str.replace('annotation_', '')
    
    # Ensure that name_alias and description columns first in annotations_df
    annotation_cols = annotations_df.columns
    annotation_cols_no_name = list(filter(lambda x: x not in ['name_alias', 'description'], annotation_cols))
    annotations_df = annotations_df[['name_alias', 'description'] + annotation_cols_no_name] # Reorder columns
    
    # Remove UUIDs from dataset identifiers for display
    dataset_df = scrnaseq_df_merged[['id_x', 'name', 'fastq_dataset_name_x']]
    dataset_df.columns = ['id', 'name', 'fastq_dataset_name']
    dataset_df['name_uuid'] = dataset_df.loc[:,'name'].str.split('_').apply(lambda x: '_'.join(x[:-1]))
    dataset_df['fastq_dataset_name_uuid'] = dataset_df.loc[:,'fastq_dataset_name'].str.split('_').apply(lambda x: '_'.join(x[:-1]))
    
    df_merged_filtered = pd.concat([dataset_df, annotations_df], axis=1)
    
    return df_merged_filtered


# continue load_full_cluster_annotation
@st.cache_data
def load_scrnaseq_cluster_annotation() -> pd.DataFrame:
    
    scrnaseq_integration = get_valid_scrnaseq_integration()
    scrnaseq_cluster_annotations = get_valid_scrnaseq_cluster_annotations()
    
    df = pd.merge(scrnaseq_integration,
                  scrnaseq_cluster_annotations,
                  how='left',
                  left_on='id',
                  right_on='scrnaseq_integration')
    
    # Return empty dataframe
    if df.empty:
        df = pd.DataFrame(columns=['name', 'description'])
        df.index.name = 'cluster'
        return df
    
    annotation = df['annotation'].values[0]
    
    s3_bucket = df['s3_bucket'].values[0]
    s3_adata_obs_key = df['s3_adata_obs_key'].values[0]
    
    adata_obs = download_df_from_s3(s3_bucket, s3_adata_obs_key)
    
    # Download cluster annotations from S3 bucket
    clusters = sorted(adata_obs['leiden'].unique())
    clusters = [str(cl) for cl in clusters] # cast str
    
    # Cast cluster annotation to wide format
    if isinstance(annotation, dict):
        for cluster in clusters:
            if cluster not in annotation:
                annotation[cluster] = {'name' : None, 'description' : None}
    elif np.isnan(annotation):
        annotation = {cluster: {'name' : None, 'description' : None} for cluster in clusters}
    else:
        raise exceptions.UIAppError("Cluster annotation is not a valid datatype")
    
    annotation_df = pd.DataFrame(annotation).T
    annotation_df.index.name = 'cluster'
    annotation_df['scrnaseq_integration_id'] = df['id_x'].values[0]
    
    annotation_df_cols = annotation_df.columns
    annotation_df_cols_no_name = list(filter(lambda x: x not in ['name', 'description'], annotation_df_cols))
    annotation_df = annotation_df[['name', 'description'] + annotation_df_cols_no_name]
    
    return annotation_df

def load_metrics() -> pd.DataFrame:
    
    scrnaseq_integration = get_valid_scrnaseq_integration()
    cluster_annotation = load_scrnaseq_cluster_annotation()
    dataset_annotation = load_scrnaseq_dataset_annotations()
    
    # If no data is found, return empty dataframes
    if scrnaseq_integration.empty:
        return pd.DataFrame(), pd.DataFrame()
    
    s3_bucket = scrnaseq_integration['s3_bucket'].values[0]
    s3_adata_obs_key = scrnaseq_integration['s3_adata_obs_key'].values[0]
    
    adata_obs = download_df_from_s3(s3_bucket, s3_adata_obs_key)
    
    adata_obs['combined'] = 'combined'
    adata_obs['leiden'] = adata_obs['leiden'].astype(str)
    
    adata_obs_annot = pd.merge(adata_obs, dataset_annotation, how='left', left_on='sample', right_on='name', suffixes=(None,'_dataset'))
    adata_obs_annot = pd.merge(adata_obs_annot, cluster_annotation, how='left', left_on='leiden', right_index=True, suffixes=(None,'_cluster'))
    
    adata_obs_annot['leiden'] = adata_obs_annot['leiden'].astype('category')
    adata_obs_annot['leiden'] = adata_obs_annot['leiden'].cat.reorder_categories(natsort.natsorted(adata_obs_annot['leiden'].unique()), ordered=True)
    
    count_metrics = adata_obs_annot[['sample', 'leiden', 'name_uuid', 'name_alias', 'name_cluster', 'combined', 'n_genes_by_counts', 'total_counts', 'n_genes']]
    count_metrics['n_genes'] = np.log10(count_metrics['n_genes']+1)
    count_metrics['n_genes_by_counts'] = np.log10(count_metrics['n_genes_by_counts']+1)
    count_metrics['total_counts'] = np.log10(count_metrics['total_counts']+1)
    
    qc_metrics = adata_obs_annot[['sample', 'leiden', 'name_uuid', 'name_alias', 'name_cluster', 'combined',
                            'pct_counts_in_top_50_genes','pct_counts_mt', 'pct_counts_ribo', 'pct_counts_hb']]
    
    return count_metrics, qc_metrics

def load_adata_umap() -> pd.DataFrame:
    
    scrnaseq_integration = get_valid_scrnaseq_integration()
    cluster_annotation = load_scrnaseq_cluster_annotation()
    dataset_annotation = load_scrnaseq_dataset_annotations()
    
    if scrnaseq_integration.empty:
        return pd.DataFrame()
    
    s3_bucket = scrnaseq_integration['s3_bucket'].values[0]
    s3_adata_obs_key = scrnaseq_integration['s3_adata_obs_key'].values[0]
    s3_umap_key = scrnaseq_integration['s3_umap_key'].values[0]
    
    adata_obs = download_df_from_s3(s3_bucket, s3_adata_obs_key)
    umap_coord_dfs = download_df_from_s3(s3_bucket, s3_umap_key)
    
    adata_obs['leiden'] = adata_obs['leiden'].astype(str)

    umap_annotation_df = pd.concat([umap_coord_dfs[['umap1', 'umap2']], 
                                    adata_obs[['sample', 'leiden']]], axis=1)
    
    umap_annotation_df = pd.merge(umap_annotation_df, dataset_annotation, how='left', left_on='sample', right_on='name', suffixes=(None,'_dataset'))
    umap_annotation_df = pd.merge(umap_annotation_df, cluster_annotation, how='left', left_on='leiden', right_index=True, suffixes=(None,'_cluster'))
    
    # Make sorted categories for leiden clusters
    umap_annotation_df['leiden'] = umap_annotation_df['leiden'].astype('category')
    umap_annotation_df['leiden'] = umap_annotation_df['leiden'].cat.reorder_categories(natsort.natsorted(umap_annotation_df['leiden'].unique()), ordered=True)
    
    return umap_annotation_df
    