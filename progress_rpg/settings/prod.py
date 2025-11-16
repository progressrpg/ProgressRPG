"""
PRODUCTION SETTINGS
Django settings for progress_rpg project.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from .base import *

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[%(asctime)s] [%(levelname)s] [%(module)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "errors": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

DEBUG = os.environ.get("DEBUG")
DB_NAME = os.environ.get("DB_NAME")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_HOST = os.environ.get("DB_HOST")
DB_PORT = os.environ.get("DB_PORT")

EMAIL_HOST = os.environ.get("EMAIL_HOST")
EMAIL_PORT = os.environ.get("EMAIL_PORT")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_PASSWORD")

print("DEBUG:", DEBUG)

REGISTRATION_ENABLED = True

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

SECRET_KEY = os.environ.get("SECRET_KEY")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "app.progressrpg.com").split(",")
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ALLOWED_ORIGINS", "https://app.progressrpg.com/"
).split(",")
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "https://app.progressrpg.com/"
).split(",")

# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

# default_db_config = dj_database_url.config(conn_max_age=60, ssl_require=True)

# if os.environ.get("RUNNING_CHANNEL_WORKER") == "1" or os.environ.get("IS_CELERY_WORKER") == "1":
#    default_db_config["CONN_MAX_AGE"] = 0

if os.environ.get("PGBOUNCER") == "1":
    pgbouncer_url = os.environ.get("DATABASE_URL_PGBOUNCER")
    if pgbouncer_url:
        os.environ["DATABASE_URL"] = pgbouncer_url
    elif "DATABASE_URL" not in os.environ:
        raise ValueError(
            "PGBOUNCER is enabled but no DATABASE_URL or DATABASE_URL_PGBOUNCER found."
        )

DB_URL = os.environ.get("DATABASE_URL")
if not DB_URL:
    raise ValueError("DATABASE_URL is not set in the environment.")

DATABASES = {"default": dj_database_url.parse(DB_URL, conn_max_age=60)}


REDIS_URL = os.environ.get("REDIS_URL")
ssl_required = os.environ.get("REDIS_VERIFY_SSL", "0") == "1"

REDIS_URL_MOD = f"{REDIS_URL}/0?ssl_cert_reqs=none"

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [
                {
                    "address": REDIS_URL_MOD,
                }
            ],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL_MOD,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # "CONNECTION_POOL_KWARGS": {
            #     "ssl_context": ssl_context,
            # }
        },
    }
}

CELERY_BROKER_URL = REDIS_URL_MOD
CELERY_RESULT_BACKEND = REDIS_URL_MOD

# CELERY_BROKER_USE_SSL = {
#     'ssl_context': ssl_context,
# }
# CELERY_REDIS_BACKEND_USE_SSL = {
#     'ssl_context': ssl_context,
# }


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
