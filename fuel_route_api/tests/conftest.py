import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_project.settings")

# Safe check
from django.apps import apps

if not apps.ready:
    django.setup()
