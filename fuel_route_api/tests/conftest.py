import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_project.settings")

# Safe check
import django
from django.apps import apps

if not apps.ready:
        django.setup()
