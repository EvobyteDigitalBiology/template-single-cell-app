import streamlit as st
import requests
import pydantic
import pandas as pd
import json
import numpy as np
    
import uiconfig
import extensions
import exceptions
import datamanager

from zihelper import aws

from uidataclasses import ScrnaseqDatasets
from uidataclasses import ScrnaseqDatasetAnnotations
from uidataclasses import ScrnaseqDatasetsIntegration
from uidataclasses import ScrnaseqClusterAnnotations

assert 'auth_status' in st.session_state, 'Auth status not found in session state'
assert 'httpauth' in st.session_state, 'HTTP Auth not found in session state'


#Set default session state
if not 'hide_uuid' in st.session_state:
    st.session_state['hide_uuid'] = True

@st.experimental_dialog("Add annotation column")
def add_annotation_column(df, session_state_key):
    col_name = st.text_input('Column Name', key='column_name_input')
    
    col1, col2 = st.columns([2,2])
    
    with col1:        
        if st.button("Add Column"):
            df[col_name] = None
            st.session_state[session_state_key] = df
            st.rerun()
    with col2: 
        if st.button("Cancel", type="secondary"):
            st.rerun()


def save_annotation(df):
    
    # Convert df back to annotations format
    scrnaseq_dataset_ids = df['id']
    df_save = df.drop(columns=['id', 'name', 'fastq_dataset_name', 'name_uuid', 'fastq_dataset_name_uuid'])
    
    for ix, row in df_save.iterrows():
        
        dataset_annotation = ScrnaseqDatasetAnnotations(
            scrnaseq_dataset=scrnaseq_dataset_ids[ix],
            annotation=row.to_dict()
        )
               
        res = requests.post(f"{uiconfig.BACKEND_API_ENDPOINT}/scrnaseq_dataset_annotations/", 
                            json=dataset_annotation.model_dump(),
                            auth=st.session_state['httpauth'])

        assert res.status_code == 201, f"Error: {res.status_code}"
    else:
        st.cache_data.clear()
        del st.session_state['annotation']

        st.toast("Save successful!", icon='😍')


def save_cluster(df):
    
    # Convert df back to annotations format
    scrnaseq_integration_id = df['scrnaseq_integration_id'].values[0]
    df_save = df.drop(columns=['scrnaseq_integration_id'])
    
    annotation = df_save.to_dict(orient='index')
    
    cluster_annotation = ScrnaseqClusterAnnotations(
        scrnaseq_integration=scrnaseq_integration_id,
        annotation=annotation
    )
    
    res = requests.post(f"{uiconfig.BACKEND_API_ENDPOINT}/scrnaseq_cluster_annotations/", 
                        json=cluster_annotation.model_dump(),
                        auth=st.session_state['httpauth'])

    assert res.status_code == 201, f"Error: {res.status_code}"
    
    st.cache_data.clear()
    del st.session_state['cluster_annotation']

    st.toast("Save successful!", icon='😍')
        
                
def update_uuid():
    st.session_state['hide_uuid'] = not st.session_state['hide_uuid']

if 'annotation' not in st.session_state:
    st.session_state['annotation'] = datamanager.load_scrnaseq_dataset_annotations()
df = st.session_state['annotation']

if 'cluster_annotation' not in st.session_state:
    st.session_state['cluster_annotation'] = datamanager.load_scrnaseq_cluster_annotation()
cluster_df = st.session_state['cluster_annotation']

# UI LOGIC

tab1, tab2 = st.tabs([":blue-background[scRNASeq Dataset Annotation]", ":blue-background[scRNASeq Cluster Annotation]"])

# TAB: scRNASeq Dataset Annotation
with tab1:

    # Test
    st.checkbox("Hide dataset UUIDs", key="hide_uuid_checkbox", value=st.session_state['hide_uuid'], on_change=update_uuid)

    if st.session_state['hide_uuid']:
        col_config = {
            'id' : None,
            'name' : None,
            'fastq_dataset_name' : None,
            'name_uuid' : st.column_config.Column("scRNASeq Identifier", disabled=True),
            'fastq_dataset_name_uuid' : st.column_config.Column("Fastq Identifier", disabled=True),
            'name_alias' : 'Name',
            'description' : 'Description'
        }
    else:
        col_config = {
            'id' : None,
            'name' : st.column_config.Column("scRNASeq Identifier", disabled=True),
            'fastq_dataset_name' : st.column_config.Column("Fastq Identifier", disabled=True),
            'name_uuid' : None,
            'fastq_dataset_name_uuid' : None,
            'name_alias' : 'Name',
            'description' : 'Description'
        }
        
    df = st.data_editor(
        df,
        hide_index=False,
        column_config=col_config,
        use_container_width = True
    )

    # Add a button to add a new annotation col
    col1, col2, col3 = st.columns([2,2,8])

    with col1:
        if st.button("Add Annotation", key='scdataset_add_annotation', type="primary"):
            add_annotation_column(df, 'annotation')

    with col2:
        st.button("Save", key = 'scdataset_save', type="primary", on_click=save_annotation, args = (df,))
        
# TAB: scRNASeq Cluster Annotation
with tab2:
    
    cluster_df = st.data_editor(
        cluster_df,
        hide_index=False,
        column_config={
            'cluster' : st.column_config.Column("Cluster", disabled=True),
            'name' : 'Name',
            'description' : 'Description',
            'scrnaseq_integration_id' : None
            },
        use_container_width = True
    )

    # Add a button to add a new annotation col
    col1, col2, col3 = st.columns([2,2,8])

    with col1:
        if st.button("Add Annotation", key='cluster_add_annotation', type="primary"):
            add_annotation_column(cluster_df, 'cluster_annotation')

    with col2:
        st.button("Save", key = 'cluster_save', type="primary", on_click=save_cluster, args = (cluster_df,))