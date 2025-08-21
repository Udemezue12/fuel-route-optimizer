from django.urls import path

from .register_controller import api
from .views import index

urlpatterns = [path("api/", api.urls), path("", index)]
