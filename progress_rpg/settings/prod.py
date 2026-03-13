"""
PRODUCTION SETTINGS
Django settings for progress_rpg project.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from .base import *
from urllib.parse import quote
from .utils import (
    get_postgres_host,
    get_redis_url,
    is_running_in_docker,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] [%(request_id)s] [%(user_id)s] [%(levelname)s] [%(name)s:%(lineno)d] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)s] [%(name)s] %(message)s",
        },
    },
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
        "request_context": {
            "()": "progress_rpg.middleware.logging_context.RequestContextFilter",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
            "filters": ["request_context"],
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "errors": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "general": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "activity": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
}

DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "yes")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")


EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = "Progress RPG <admin@progressrpg.com>"

print("DEBUG:", DEBUG, file=sys.stderr)

REGISTRATION_ENABLED = True

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

SECRET_KEY = os.environ.get("SECRET_KEY")

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "staging.progressrpg.com,app.progressrpg.com,progressrpg.onrender.com",
).split(",")
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS",
    "https://staging.progressrpg.com,https://app.progressrpg.com,https://progressrpg.onrender.com",
).split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "https://staging.progressrpg.com,https://app.progressrpg.com,https://progressrpg.onrender.com",
).split(",")

# ------------------------------
# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases
# ------------------------------


# DB_NAME = os.getenv("DB_NAME", "progressrpg_staging")
# DB_USER = os.getenv("DB_USER", default="duncan")
# DB_PASSWORD = os.getenv("DB_PASSWORD", "")
# DB_PORT = os.getenv("DB_PORT", default=5432)

# IN_DOCKER = is_running_in_docker()

DATABASE_URL = os.environ.get("DATABASE_URL")
# if not DATABASE_URL:
#     # Fallback to explicit DB_* vars for local dev
#     DB_USER = os.environ.get("DB_USER", "duncan")
#     DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
#     DB_NAME = os.environ.get("DB_NAME", "progressrpg")
#     DB_HOST = get_postgres_host()
#     DB_PORT = os.environ.get("DB_PORT", 5432)
#     DATABASE_URL = f"postgres://{DB_USER}:{quote(DB_PASSWORD, safe='')}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

db = dj_database_url.parse(DATABASE_URL, conn_max_age=60)
db["ENGINE"] = "django.contrib.gis.db.backends.postgis"
DATABASES = {"default": db}


REDIS_URL_MOD = get_redis_url(default_db="0")


# ssl_context = ssl.create_default_context()
# ssl_context.check_hostname = False
# ssl_context.verify_mode = ssl.CERT_NONE

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL_MOD],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL_MOD,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

CELERY_BROKER_URL = REDIS_URL_MOD
CELERY_RESULT_BACKEND = REDIS_URL_MOD

# Session settings
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_SAVE_EVERY_REQUEST = False

SESSION_COOKIE_NAME = "sessionid"
# SESSION_COOKIE_DOMAIN = '.progressrpg.com'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 86400  # 24 hours in seconds

CSRF_COOKIE_SECURE = True
# CSRF_COOKIE_DOMAIN = '.progressrpg.com'

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = []
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
