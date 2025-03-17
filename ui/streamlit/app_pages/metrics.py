import streamlit as st
import requests
import pydantic
import pandas as pd
import json
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

from zihelper import aws

import uiconfig
import extensions
import exceptions
import warnings
import datamanager
from uidataclasses import ScrnaseqDatasetsIntegration

pd.set_option('mode.chained_assignment', None)

assert 'auth_status' in st.session_state, 'Auth status not found in session state'
assert 'httpauth' in st.session_state, 'HTTP Auth not found in session state'


def update_grouping():
    identifier_val = st.session_state.metrics_grouping
    grouping_map = {'Combined': 'combined', 'Dataset': 'sample', 'Cluster': 'leiden'}
    st.session_state['grouping'] = grouping_map[identifier_val]

def update_type():
    st.session_state['metrics_type'] = st.session_state.metrics_type

def update_sample_identifier():
    identifier_val = st.session_state.metrics_sample_identifier
    sample_id_map = {'ID': 'sample', 'ID-Short': 'name_uuid', 'Name': 'name_alias'}
    st.session_state['sample_identifier'] = sample_id_map[identifier_val]

def update_cluster_identifier():
    identifier_val = st.session_state.metrics_cluster_identifier
    cluster_id_map = {'ID': 'leiden', 'Name': 'name_cluster'}
    st.session_state['cluster_identifier'] = cluster_id_map[identifier_val]

if not 'grouping' in st.session_state:
    st.session_state['grouping'] = 'combined'
grouping = st.session_state['grouping']

if not 'metrics_type' in st.session_state:
    st.session_state['metrics_type'] = 'Counts'
metrics_type = st.session_state['metrics_type']

if not 'sample_identifier' in st.session_state:
    st.session_state['sample_identifier'] = 'sample'
sample_identifier = st.session_state['sample_identifier']

if not 'cluster_identifier' in st.session_state:
    st.session_state['cluster_identifier'] = 'leiden'
cluster_identifier = st.session_state['cluster_identifier']

metrics_df, qc_metrics_df = datamanager.load_metrics()

col1, col2 = st.columns([10,2])

with col1:
    
    if metrics_df.empty or qc_metrics_df.empty:
        st.warning('No datasets found.')

    else:
        
        if metrics_type == 'Counts':
            metrics_long_df = metrics_df.melt(id_vars=['sample', 'leiden', 'name_uuid', 'name_alias', 'name_cluster', 'combined'], 
                                            var_name='metric', value_name='value')
            input_df = metrics_long_df
            ylabel = 'log10(count+1)'
            titles = ['Number of Genes by Counts', 'Total Counts', 'Number of Genes']
                    
        else:
            qc_metrics_long_df = qc_metrics_df.melt(id_vars=['sample', 'leiden', 'name_uuid', 'name_alias', 'name_cluster', 'combined'],
                                                    var_name='metric', value_name='value')
            input_df = qc_metrics_long_df
            ylabel = '%'
            titles = ['Top50 Gene Counts', 'Mito Counts', 'Ribo Counts', 'Hb Counts']
        
        if grouping == 'sample':
            x_var = sample_identifier
        elif grouping == 'leiden':
            x_var = cluster_identifier
        else:
            x_var = 'combined'
        
        st.divider()
            
        g = sns.FacetGrid(input_df, col='metric')
        g.map(sns.violinplot, x_var, 'value')
        g.set_xlabels('datasets')
        g.set_ylabels(ylabel)
        _ = [g.axes[0,i].set_title(t) for i, t in enumerate(titles)]

        # Rotate x-axis labels if they are too long
        if input_df[x_var].astype(str).str.len().max() > 2:
            g.set_xticklabels(rotation=90)

        st.pyplot(g)
    
with col2:
    
    st.divider()
    
    st.write('')
    st.write('')
    
    st.radio('Select grouping', ['Combined', 'Dataset', 'Cluster'], index=0, key='metrics_grouping', on_change = update_grouping)
    
    # Conditional grouping to select dataset identifier to show
    if grouping == 'sample':
        st.radio('Sample Identifer', ['ID', 'ID-Short', 'Name'], index=0, key='metrics_sample_identifier', on_change = update_sample_identifier)
        
    elif grouping == 'leiden':
        st.radio('Cluster Identifier', ['ID', 'Name'], index=0, key='metrics_cluster_identifier', on_change = update_cluster_identifier)
    
    st.radio('Select metric', ['Counts', 'QC'], index=0, key='metrics_type', on_change = update_type)
    
    