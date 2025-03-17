# case-scrnaseq/django/backend/scrnaseq/apps.py

from django.apps import AppConfig


class ScrnaseqConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scrnaseq'
