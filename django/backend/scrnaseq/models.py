# case-scrnaseq/django/backend/scrnaseq/models.py

from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class FastqDatasets(models.Model):
    
    name = models.TextField(unique=True)
    s3_bucket = models.TextField()
    s3_source_key = models.TextField()
    s3_source_bucket = models.TextField()
    s3_read1_fastq_key = models.TextField()
    s3_read2_fastq_key = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, related_name='fastq_datasets', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'fastq_datasets'
        
class ScrnaseqDatasets(models.Model):
    
    name = models.TextField(unique=True)
    fastq_dataset = models.ForeignKey(FastqDatasets, related_name='scrnaseq_datasets', on_delete=models.CASCADE)
    transcriptome = models.TextField()
    s3_bucket = models.TextField()
    s3_qc_metrics_key = models.TextField()
    s3_gene_expression_matrix_key = models.TextField()
    s3_gene_expression_matrix_size_mb = models.FloatField()
    number_cells = models.IntegerField()
    mean_reads_per_cell = models.IntegerField()
    median_number_genes_per_cell = models.IntegerField()
    total_number_reads = models.IntegerField()
    pipeline_version = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    valid_from = models.DateTimeField(auto_now=True)
    valid_to = models.DateTimeField(null=True)
    owner = models.ForeignKey(User, related_name='scrnaseq_datasets', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'scrnaseq_datasets'
        
class ScrnaseqIntegration(models.Model):
    
    name = models.TextField(unique=True)
    scrnaseq_dataset = models.ManyToManyField(ScrnaseqDatasets, related_name='scrnaseq_integration')
    min_genes_per_cell = models.IntegerField()
    min_cells_per_gene = models.IntegerField()
    num_highly_variable_genes = models.IntegerField()
    num_pcs = models.IntegerField()
    leiden_resolution = models.FloatField()
    s3_bucket = models.TextField()
    s3_adata_key = models.TextField()
    s3_umap_key = models.TextField()
    s3_adata_obs_key = models.TextField()
    pipeline_version = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    valid_from = models.DateTimeField(auto_now=True)
    valid_to = models.DateTimeField(null=True)
    owner = models.ForeignKey(User, related_name='scrnaseq_integration', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'scrnaseq_integration'
        
class ScrnaseqDatasetAnnotations(models.Model):
    
    scrnaseq_dataset = models.ForeignKey(ScrnaseqDatasets, related_name='scrnaseq_dataset_annotations', on_delete=models.CASCADE)
    annotation = models.JSONField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    valid_from = models.DateTimeField(auto_now=True)
    valid_to = models.DateTimeField(null=True)
    owner = models.ForeignKey(User, related_name='scrnaseq_dataset_annotations', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'scrnaseq_dataset_annotations'
    

class ScrnaseqClusterAnnotations(models.Model):
    
    scrnaseq_integration = models.ForeignKey(ScrnaseqIntegration, related_name='scrnaseq_cluster_annotations', on_delete=models.CASCADE)
    annotation = models.JSONField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    valid_from = models.DateTimeField(auto_now=True)
    valid_to = models.DateTimeField(null=True)
    owner = models.ForeignKey(User, related_name='scrnaseq_cluster_annotations', on_delete=models.CASCADE)
    
    class Meta:
        db_table = 'scrnaseq_cluster_annotations'