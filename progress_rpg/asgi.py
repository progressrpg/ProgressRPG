"""
ASGI config for progress_rpg project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

import django

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "progress_rpg.settings.prod"),
)

django.setup()

from gameplay.routing import load_websocket_urlpatterns
from progress_rpg.middleware.channels_jwt import JWTQueryStringAuthMiddlewareStack

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": JWTQueryStringAuthMiddlewareStack(
            URLRouter(load_websocket_urlpatterns()),
        ),
    }
)
