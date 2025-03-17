import datetime
from pydantic import BaseModel, Json
from typing import List, Dict

class ScrnaseqDatasets(BaseModel):
    id : int
    name: str
    fastq_dataset : int
    fastq_dataset_name : str
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
    
class ScrnaseqDatasetAnnotations(BaseModel):
    id : int | None = None
    scrnaseq_dataset: int
    scrnaseq_dataset_name: str | None = None
    fastq_dataset_name: str | None = None
    annotation: Dict
    valid_from : datetime.datetime | None = None
    valid_to : datetime.datetime | None = None
    
class ScrnaseqDatasetsIntegration(BaseModel):
    id: int
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
    valid_from : datetime.datetime
    valid_to : datetime.datetime | None
    
class ScrnaseqClusterAnnotations(BaseModel):
    id : int | None = None
    scrnaseq_integration: int
    annotation: Dict
    valid_from : datetime.datetime | None = None
    valid_to : datetime.datetime | None = None