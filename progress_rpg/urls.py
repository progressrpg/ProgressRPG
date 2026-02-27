"""
URL configuration for progress_rpg project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseNotFound
from django.urls import re_path, path, include
from django.views.generic import TemplateView
from django.views.static import serve


# from gameplay.admin import custom_admin_site

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/v1/", include("api.urls")),
    path("", include("users.urls")),
    path("", include("payments.urls")),
    path("", include("gameworld.urls")),
    path("", include("server_management.urls")),
    re_path(
        r"^static/(?P<path>.*)$",
        serve,
        {"document_root": settings.STATIC_ROOT},
    ),
    re_path(r"^\.well-known/.*$", lambda request: HttpResponseNotFound()),
    re_path(
        r"^(?!api|admin|static|media|ws).*",
        TemplateView.as_view(template_name="index.html"),
    ),
]

""" # Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) """
