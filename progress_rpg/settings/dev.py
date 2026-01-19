"""
LOCAL DEVELOPMENT SETTINGS
Django settings for progress_rpg project.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from .base import *
from .utils import (
    get_branch_name,
    get_branch_db_name,
    ensure_branch_db_exists,
    migrate_and_seed,
)
import subprocess


BRANCH_NAME = get_branch_name()
print("BRANCH_NAME is:", BRANCH_NAME)

new_db_created = ensure_branch_db_exists()

DB_NAME = get_branch_db_name()

ROOT_URLCONF = "progress_rpg.urls"


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] [%(request_id)s] [%(user_id)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "file_info": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/general.log"),
            "formatter": "verbose",
            "maxBytes": 5 * 1024 * 1024,  # 5MB per file
            "backupCount": 3,  # Keep last 3 log files
        },
        "file_errors": {
            "level": "ERROR",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/errors.log"),
            "formatter": "verbose",
            "maxBytes": 5 * 1024 * 1024,  # 5MB per file
            "backupCount": 3,  # Keep last 3 log files
        },
        "file_debug": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(BASE_DIR, "logs/activity.log"),
            "formatter": "verbose",
            "maxBytes": 5 * 1024 * 1024,  # 5MB per file
            "backupCount": 6,  # Keep last 5 log files
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],  # "file_errors"
            "level": "DEBUG",
            "propagate": False,
        },
        "errors": {
            "handlers": ["file_errors"],
            "level": "ERROR",
            "propagate": False,
        },
        "general": {
            "handlers": ["file_info"],
            "level": "INFO",
            "propagate": False,
        },
        "activity": {
            "handlers": ["file_debug"],
            "level": "DEBUG",
            "propagate": False,
        },
        "django.db.backends": {
            "level": "WARNING",
            "handlers": ["console", "file_errors"],
            "propagate": False,
        },
    },
}


dotenv_path = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path)

REGISTRATION_ENABLED = True
SECRET_KEY_FALLBACKS = [
    "django-insecure-46)84p=e^!*as-px9&4pl0jqh7wfy$clbwtu3(%9$qj&(5ri-$"
]

DEBUG = os.getenv("DEBUG", "True") == "True"


DB_USER = os.getenv("DB_USER", default="duncan")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", default="localhost")
DB_PORT = os.getenv("DB_PORT", default=5432)

DATABASE_URL = f"postgres://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False

print("DEBUG:", DEBUG)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1").replace("\r", "").split(",")
# ALLOWED_HOSTS = ["*"]
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", "http://127.0.0.1,http://localhost:8000"
).split(",")
CSRF_TRUSTED_ORIGINS = os.getenv(
    "CSRF_TRUSTED_ORIGINS", "http://127.0.0.1,http://localhost:8000"
).split(",")

print("ALLOWED HOSTS:", ALLOWED_HOSTS)
print("CORS:", CORS_ALLOWED_ORIGINS)


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases


DATABASES = {"default": dj_database_url.parse(DATABASE_URL, conn_max_age=60)}


REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
# print("REDIS_URL:", REDIS_URL)
# PRETEND = f"{REDIS_URL}?ssl_cert_reqs=none"
# print("PRETEND:", PRETEND)

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
    }
}


# For local development only
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = True

SESSION_COOKIE_NAME = "sessionid"
SESSION_COOKIE_DOMAIN = None
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 3600  # 1 hour in seconds

CSRF_COOKIE_DOMAIN = None
CSRF_COOKIE_SECURE = False

SECURE_PROXY_SSL_HEADER = None
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"

CELERY_RESULT_BACKEND = "redis://localhost:6379/0"
CELERY_BROKER_URL = "redis://localhost:6379/0"
