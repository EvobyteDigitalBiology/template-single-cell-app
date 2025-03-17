import streamlit as st
import requests
import pydantic
import pandas as pd
import json
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

import uiconfig
import extensions
import exceptions
import warnings
import datamanager


from zihelper import aws

from uidataclasses import ScrnaseqDatasetsIntegration

pd.set_option('mode.chained_assignment', None)

assert 'auth_status' in st.session_state, 'Auth status not found in session state'
assert 'httpauth' in st.session_state, 'HTTP Auth not found in session state'

# TODO: Check what happens if there are no annotations
def get_valid_scrnaseq_integration() -> pd.DataFrame():
    
    res = requests.get(f"{uiconfig.BACKEND_API_ENDPOINT}/scrnaseq_integration/get_valid/", auth=st.session_state['httpauth'])
    
    dataset_integration = ScrnaseqDatasetsIntegration(**res.json())
    
    assert res.status_code == 200, f"Error: {res.status_code}"
    
    # Empty list case: get dataframe with empty columns
    df = pd.DataFrame(dataset_integration.dict())
    df.drop(columns=['scrnaseq_dataset'], inplace=True)
    df.drop_duplicates(inplace=True)
    
    return df

def load_adata_umap():
    
    aws_s3 = aws.AwsS3()
    
    scrnaseq_integration = datamanager.get_valid_scrnaseq_integration() # Could come from session state
    
    s3_bucket = scrnaseq_integration['s3_bucket'].values[0]
    s3_umap_key = scrnaseq_integration['s3_umap_key'].values[0]
    s3_adata_obs_key = scrnaseq_integration['s3_adata_obs_key'].values[0]
    
    umap_coord_dfs = pd.read_csv(f"s3://{s3_bucket}/{s3_umap_key}")
    adata_obs_df = pd.read_csv(f"s3://{s3_bucket}/{s3_adata_obs_key}")
    
    umap_annotation_df = pd.concat([umap_coord_dfs[['umap1', 'umap2']], adata_obs_df[['sample', 'leiden']]], axis=1)
    umap_annotation_df['leiden'] = umap_annotation_df['leiden'].astype('category')
    
    return umap_annotation_df

def update_umap_grouping():
    st.session_state['umap_grouping'] = st.session_state['explorer_umap_grouping']

def update_sample_identifier():
    identifier_val = st.session_state.metrics_sample_identifier
    sample_id_map = {'ID': 'sample', 'ID-Short': 'name_uuid', 'Name': 'name_alias'}
    st.session_state['sample_identifier'] = sample_id_map[identifier_val]

def update_cluster_identifier():
    identifier_val = st.session_state.metrics_cluster_identifier
    cluster_id_map = {'ID': 'leiden', 'Name': 'name_cluster'}
    st.session_state['cluster_identifier'] = cluster_id_map[identifier_val]

if not 'sample_identifier' in st.session_state:
    st.session_state['sample_identifier'] = 'sample'
sample_identifier = st.session_state['sample_identifier']

if not 'cluster_identifier' in st.session_state:
    st.session_state['cluster_identifier'] = 'leiden'
cluster_identifier = st.session_state['cluster_identifier']

    
if not 'umap_grouping' in st.session_state:
    st.session_state['umap_grouping'] = 'leiden'
umap_grouping = st.session_state['umap_grouping']

umap_df = datamanager.load_adata_umap()

col1, col2, col3 = st.columns([7,1,4])

# Option to add stereo view

with col1:

    if umap_df.empty:
        st.warning('No datasets found.')
    
    else:
        st.divider()
        
        if umap_grouping == 'sample':
            x_var = sample_identifier
        elif umap_grouping == 'leiden':
            x_var = cluster_identifier
        
        resolution = st.slider("Graph Resolution", min_value = 5, max_value = 20, step = 5, value = 10)
        
        fig, ax = plt.subplots(figsize=(resolution, resolution))
        sns.scatterplot(data=umap_df, x='umap1', y='umap2', hue=x_var, ax=ax)
        ax.legend(bbox_to_anchor=(1.15, 1))
        
        st.pyplot(fig, {'pad_inches':12})
        
with col3:
    
    st.divider()
    
    st.write('')
    st.write('')
    
    st.radio('Select grouping', ['sample', 'leiden'], index=0, key='explorer_umap_grouping', on_change = update_umap_grouping)

    # Conditional grouping to select dataset identifier to show
    if umap_grouping == 'sample':
        st.radio('Sample Identifer', ['ID', 'ID-Short', 'Name'], index=0, key='metrics_sample_identifier', on_change = update_sample_identifier)
        
    elif umap_grouping == 'leiden':
        st.radio('Cluster Identifier', ['ID', 'Name'], index=0, key='metrics_cluster_identifier', on_change = update_cluster_identifier)
    