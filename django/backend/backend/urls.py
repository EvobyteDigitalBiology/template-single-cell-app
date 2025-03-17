# case-scrnaseq/django/backend/backend/urls.py

"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import routers

from scrnaseq import views


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'fastq_datasets', views.FastqDatasetsViewSet)
router.register(r'scrnaseq_datasets', views.ScrnaseqDatasetsViewSet)
router.register(r'scrnaseq_integration', views.ScrnaseqIntegrationViewSet)
router.register(r'scrnaseq_dataset_annotations', views.ScrnaseqDatasetAnnotationsViewSet)
router.register(r'scrnaseq_cluster_annotations', views.ScrnaseqClusterAnnotationsViewSet)

#CheckUserGroupView

urlpatterns = [
    path('api_v1/', include(router.urls)),
    path('admin/', admin.site.urls),
    path('api_v1/fastq_datasets/get_by_s3_read2_fastq_key/', views.FastqDatasetsViewSet.as_view({'get': 'get_by_s3_read2_fastq_key'})),
    path('api_v1/scrnaseq_datasets/get_valid/', views.ScrnaseqDatasetsViewSet.as_view({'get': 'get_valid'})),
    path('api_v1/scrnaseq_integration/get_valid/', views.ScrnaseqIntegrationViewSet.as_view({'get': 'get_valid'})),
    path('api_v1/scrnaseq_dataset_annotations/get_valid/', views.ScrnaseqDatasetAnnotationsViewSet.as_view({'get': 'get_valid'})),
    path('api_v1/scrnaseq_cluster_annotations/get_valid/', views.ScrnaseqClusterAnnotationsViewSet.as_view({'get': 'get_valid'})),
    path('api_v1/check_user_group/', views.CheckUserGroupView.as_view()),
]