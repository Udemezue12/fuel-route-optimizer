import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuel_project.settings')


import django
from django.apps import apps

if not apps.ready:
        django.setup()

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.staticfiles import StaticFiles
from starlette.routing import Mount
from django.core.asgi import get_asgi_application
from django.conf import settings
from fuel_route_api.env import SECRET_KEY
from fuel_route_api.loaders.fuel_station_loader import FuelStationLoader

django_app = get_asgi_application()

async def startup():
    loader = FuelStationLoader()
    result = await loader.async_load()
    print(f"[Startup] {result}")

application = Starlette(
    routes=[
        Mount("/static", app=StaticFiles(directory=settings.STATIC_ROOT), name="static"),
        Mount("/", app=django_app),
    ],
    middleware=[
        Middleware(SessionMiddleware, secret_key=SECRET_KEY),
    ],
    on_startup=[startup]
)
