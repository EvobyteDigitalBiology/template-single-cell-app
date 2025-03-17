# case-scrnaseq/django/backend/scrnaseq/serializers.py

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import FastqDatasets
from .models import ScrnaseqDatasets
from .models import ScrnaseqIntegration
from .models import ScrnaseqDatasetAnnotations
from .models import ScrnaseqClusterAnnotations

class UserSerializer(serializers.ModelSerializer):
    fastq_datasets = serializers.PrimaryKeyRelatedField(many=True,
                                                       queryset=FastqDatasets.objects.all())

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'fastq_datasets']

class FastqDatasetsSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = FastqDatasets
        fields = ('id',
                  'name',
                  's3_bucket',
                  's3_source_key',
                  's3_source_bucket',
                  's3_read1_fastq_key', 
                  's3_read2_fastq_key')

class ScrnaseqDatasetsSerializer(serializers.HyperlinkedModelSerializer):
    
    fastq_dataset = serializers.PrimaryKeyRelatedField(queryset=FastqDatasets.objects.all())

    fastq_dataset_name = serializers.CharField(source='fastq_dataset.name', read_only=True)
    
    class Meta:
        model = ScrnaseqDatasets
        fields = ('id',
                  'name',
                  'fastq_dataset',
                  'fastq_dataset_name',
                  'transcriptome',
                  's3_bucket',
                  's3_qc_metrics_key',
                  's3_gene_expression_matrix_key',
                  's3_gene_expression_matrix_size_mb', 
                  'number_cells',
                  'mean_reads_per_cell',
                  'median_number_genes_per_cell', 
                  'total_number_reads',
                  'pipeline_version',
                    'valid_from',
                    'valid_to',
                )
        
class ScrnaseqIntegrationSerializer(serializers.HyperlinkedModelSerializer):
    scrnaseq_dataset = serializers.PrimaryKeyRelatedField(queryset=ScrnaseqDatasets.objects.all(), 
                                                          many=True)
    
    class Meta:
        model = ScrnaseqIntegration
        fields = ('id',
                  'name',
                  'scrnaseq_dataset',
                  'min_genes_per_cell',
                  'min_cells_per_gene',
                  'num_highly_variable_genes',
                  'num_pcs',
                  'leiden_resolution', 
                  's3_bucket',
                  's3_adata_key',
                  's3_umap_key', 
                  's3_adata_obs_key',
                  'pipeline_version',
                  'valid_from',
                  'valid_to'
                )
              
class ScrnaseqDatasetAnnotationsSerializer(serializers.HyperlinkedModelSerializer):

    scrnaseq_dataset = serializers.PrimaryKeyRelatedField(queryset=ScrnaseqDatasets.objects.all(), 
                                                          many=False)
    
    scrnaseq_dataset_name = serializers.CharField(source='scrnaseq_dataset.name', read_only=True)
    fastq_dataset_name = serializers.CharField(source='scrnaseq_dataset.fastq_dataset.name', read_only=True)
    
    class Meta:
        model = ScrnaseqDatasetAnnotations
        fields = ('id',
                  'scrnaseq_dataset',
                  'scrnaseq_dataset_name',
                  'fastq_dataset_name',
                  'annotation',
                  'valid_from',
                  'valid_to'
                )
        
class ScrnaseqClusterAnnotationsSerializer(serializers.HyperlinkedModelSerializer):
    
    scrnaseq_integration = serializers.PrimaryKeyRelatedField(queryset=ScrnaseqIntegration.objects.all(), 
                                                          many=False)
    
    class Meta:
        model = ScrnaseqClusterAnnotations
        fields = ('id',
                  'scrnaseq_integration',
                  'annotation',
                  'valid_from',
                  'valid_to'
                )