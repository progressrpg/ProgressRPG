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
from asgiref.sync import SyncToAsync

# from channels.auth import AuthMiddlewareStack
# from gameplay.mymiddleware import MyAuthMiddleware

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    os.getenv("DJANGO_SETTINGS_MODULE", "progress_rpg.settings.dev"),
)

django.setup()

from django_channels_jwt.middleware import JwtAuthMiddlewareStack
from gameplay.routing import load_websocket_urlpatterns

django_asgi_app = get_asgi_application()
application = ProtocolTypeRouter(
    {
        "http": SyncToAsync(django_asgi_app, thread_sensitive=True),
        "websocket": JwtAuthMiddlewareStack(
            URLRouter(load_websocket_urlpatterns()),
        ),
    }
)
