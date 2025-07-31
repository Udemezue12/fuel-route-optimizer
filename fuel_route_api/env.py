import os
from dotenv import load_dotenv
load_dotenv()


SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = os.getenv('ALGORITHM')
TOMTOM_API_KEY = os.getenv('TOMTOM_API_KEY')
TOMTOM_BASE_URL = os.getenv('TOMTOM_BASE_URL')
MAPBOX_BASE_URL = os.getenv('MAPBOX_BASE_URL')
MAPBOX_API_KEY = os.getenv('MAPBOX_API_KEY')
GEOAPIFY_API_KEY = os.getenv('GEOAPIFY_API_KEY')
GEOAPIFY_BASE_URL = os.getenv('GEOAPIFY_BASE_URL')
