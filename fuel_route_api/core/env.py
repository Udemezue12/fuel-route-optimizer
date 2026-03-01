import os

from dotenv import load_dotenv

from .url_parser import parser

load_dotenv()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
TOMTOM_BASE_URL = os.getenv("TOMTOM_BASE_URL")
MAPBOX_BASE_URL = os.getenv("MAPBOX_BASE_URL")
MAPBOX_API_KEY = os.getenv("MAPBOX_API_KEY")
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
GEOAPIFY_BASE_URL = os.getenv("GEOAPIFY_BASE_URL")
CELERY_REDIS_URL = os.getenv("CELERY_REDIS_URL")
RESET_SECRET_KEY: str | None = os.getenv("RESET_SECRET_KEY")
VERIFY_EMAIL_SECRET_KEY: str | None = os.getenv("VERIFY_EMAIL_SECRET_KEY")
RESET_PASSWORD_SALT: str = "password-reset-salt"
VERIFY_EMAIL_SALT: str = "verify-reset-salt"
TERMII_BASE_URL = os.getenv("TERMII_BASE_URL")
TERMII_API_KEY = os.getenv("TERMII_API_KEY")
TERMII_SENDER_ID = os.getenv("TERMII_SENDER_ID")
EMAIL_USER: str | None = os.getenv("EMAIL_USER")
EMAIL_PASSWORD: str | None = os.getenv("EMAIL_PASSWORD")
EMAIL_SERVER: str | None = os.getenv("EMAIL_SERVER")
EMAIL_PORT: int = 587
EMAIL_USE_TLS: bool = True
FRONTEND_URL: str | None = os.getenv("FRONTEND_URL")
ALLOWED_ORIGIN_RAW: str = os.getenv("ALLOWED_ORIGINS", "")
CORS_ALLOWED_HOSTS_RAW:str = os.getenv("CORS_ALLOWED_HOSTS", "")
CSRF_TRUSTED_HOSTS_RAW:str=os.getenv("CSRF_TRUSTED_HOSTS", "")
ALLOWED_ORIGINS = parser.parsers_list(ALLOWED_ORIGIN_RAW)
CORS_ALLOWED_HOSTS = parser.parsers_list(CORS_ALLOWED_HOSTS_RAW)
CSRF_TRUSTED_HOSTS = parser.parsers_list(CSRF_TRUSTED_HOSTS_RAW)