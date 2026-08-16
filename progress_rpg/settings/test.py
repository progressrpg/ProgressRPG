from .dev import *


######## TEST-SPECIFIC SETTINGS ###############

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Tests hit the cache a lot (online-count, disconnect-task bookkeeping, etc.).
# Use an in-process cache instead of real Redis to cut out network round-trips.
# Many tests rely on `cache.clear()` to also reset rate-limit counters, which
# only works if ratelimiting shares this same in-process cache rather than a
# separately-cleared real Redis one (that let counters accumulate across the
# whole test run and started 403-ing unrelated tests).
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    },
}

# django_ratelimit's checks assume a shared, multi-process cache (Redis/
# memcached) for production safety. Locmem is fine here: tests run in a
# single process, and it's what makes `cache.clear()` reset rate limits too.
SILENCED_SYSTEM_CHECKS = ["django_ratelimit.E003", "django_ratelimit.W001"]

LOGGING = {
    "version": 1,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
        },
    },
}
