# case-scrnaseq/django/backend/scrnaseq/views.py

import datetime
from django.contrib.auth.models import User
from django.shortcuts import render

from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView


from .serializers import UserSerializer
from .serializers import FastqDatasetsSerializer
from .serializers import ScrnaseqDatasetsSerializer
from .serializers import ScrnaseqIntegrationSerializer
from .serializers import ScrnaseqDatasetAnnotationsSerializer
from .serializers import ScrnaseqClusterAnnotationsSerializer

from .models import FastqDatasets
from .models import ScrnaseqDatasets
from .models import ScrnaseqIntegration
from .models import ScrnaseqDatasetAnnotations
from .models import ScrnaseqClusterAnnotations

# Create your views here.
class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    
    permission_classes = [permissions.IsAuthenticated,
                          permissions.DjangoModelPermissions]
    
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class CheckUserGroupView(APIView):
    # Set permission classes
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, format=None):
        group = request.query_params.get('group')
        
        # If user is superuser, return success
        if request.user.is_superuser:
            return Response({"message": "authorized via superuser"})
        
        if not group:
            return Response({"error": "group parameter required"}, status=400)
    
        # Your logic here, for example, just return a success message
        u_groups = User.objects.get(username=request.user).groups.filter(name=group).first()
        
        if u_groups:
            return Response({"message": "authorized via group permissions"})
        else:
            return Response({"message": "invalid group permissions"})

# TODO Update return many
class FastqDatasetsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows FastqDatasets to be viewed or edited.
    """
    
    permission_classes = [permissions.IsAuthenticated,
                          permissions.DjangoModelPermissions]
    
    queryset = FastqDatasets.objects.all().order_by('-created')
    serializer_class = FastqDatasetsSerializer
    
    def perform_create(self, serializer):    
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'])
    def get_by_s3_read2_fastq_key(self, request):
        
        s3_read2_fastq_key = request.query_params.get('s3_read2_fastq_key')
        if s3_read2_fastq_key:
            qset = FastqDatasets.objects.filter(s3_read2_fastq_key=s3_read2_fastq_key).first()
            serializer = self.get_serializer(qset)
            return Response(serializer.data)
        else:
            return Response({"error": "read2 parameter is required"}, status=400)
        
        
class ScrnaseqDatasetsViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows ScrnaseqDatasets to be viewed or edited
    """
    
    permission_classes = [permissions.IsAuthenticated,
                          permissions.DjangoModelPermissions]
    
    queryset = ScrnaseqDatasets.objects.all().order_by('-created')
    serializer_class = ScrnaseqDatasetsSerializer
    
    def perform_create(self, serializer):
        
        fastq_dataset = serializer.validated_data.get('fastq_dataset')
        
        # Update last dataset
        q_last = ScrnaseqDatasets.objects.filter(fastq_dataset=fastq_dataset, valid_to=None).first()
        
        if q_last:
            q_last.valid_to = datetime.datetime.now()
            q_last.save()
        
        serializer.save(owner=self.request.user)
    
    @action(detail=False, methods=['get'])
    def get_valid(self, request):
        
        qset = ScrnaseqDatasets.objects.filter(valid_to=None).all()
                
        serializer = self.get_serializer(qset, many=True)
        return Response(serializer.data)
    
        
class ScrnaseqIntegrationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows ScrnaseqDatasets to be viewed or edited
    """
    
    permission_classes = [permissions.IsAuthenticated,
                          permissions.DjangoModelPermissions]
    
    queryset = ScrnaseqIntegration.objects.all().order_by('-created')
    serializer_class = ScrnaseqIntegrationSerializer
    
    def perform_create(self, serializer):
        
        # Update last dataset
        q_last = ScrnaseqIntegration.objects.filter(valid_to=None).first()
        
        if q_last:
            q_last.valid_to = datetime.datetime.now()
            q_last.save()
        
        serializer.save(owner=self.request.user)
        
    @action(detail=False, methods=['get'])
    def get_valid(self, request):
        
        qset = ScrnaseqIntegration.objects.filter(valid_to=None).all()
        
        if len(qset) > 1:
            return Response({"error": "Multi valid dataset found."}, status=400)
        else:        
            serializer = self.get_serializer(qset, many=True)
            return Response(serializer.data)
        
class ScrnaseqDatasetAnnotationsViewSet(viewsets.ModelViewSet):
    
    permission_classes = [permissions.IsAuthenticated,
                          permissions.DjangoModelPermissions]
    
    queryset = ScrnaseqDatasetAnnotations.objects.all().order_by('-created')
    serializer_class = ScrnaseqDatasetAnnotationsSerializer
    
    def perform_create(self, serializer):
        
        scrnaseq_dataset = serializer.validated_data.get('scrnaseq_dataset')
        q_last = ScrnaseqDatasetAnnotations.objects.filter(valid_to=None, scrnaseq_dataset=scrnaseq_dataset).first()
        
        if q_last:
            q_last.valid_to = datetime.datetime.now()
            q_last.save()
        
        serializer.save(owner=self.request.user)
        
    @action(detail=False, methods=['get'])
    def get_valid(self, request):
        
        qset = ScrnaseqDatasetAnnotations.objects.filter(valid_to=None).all()
                
        serializer = self.get_serializer(qset, many=True)
        return Response(serializer.data)

class ScrnaseqClusterAnnotationsViewSet(viewsets.ModelViewSet):
    
    permission_classes = [permissions.IsAuthenticated,
                          permissions.DjangoModelPermissions]
    
    queryset = ScrnaseqClusterAnnotations.objects.all().order_by('-created')
    serializer_class = ScrnaseqClusterAnnotationsSerializer
    
    def perform_create(self, serializer):
        
        # Update last dataset
        q_last = ScrnaseqClusterAnnotations.objects.filter(valid_to=None).first()
        
        if q_last:
            q_last.valid_to = datetime.datetime.now()
            q_last.save()
        
        serializer.save(owner=self.request.user)
        
    @action(detail=False, methods=['get'])
    def get_valid(self, request):
        
        qset = ScrnaseqClusterAnnotations.objects.filter(valid_to=None).all()
        
        if len(qset) > 1:
            return Response({"error": "Multi valid dataset found."}, status=400)
        else:
            serializer = self.get_serializer(qset, many=True)
            return Response(serializer.data)