from django.shortcuts import render
from django.views.decorators.cache import cache_page
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import MaintenanceWindow


# @cache_page(60 * 15)
def maintenance_view(request):
    profile = request.user.profile

    return render(request, "server_management/maintenance.html", {"profile": profile})


@api_view(["GET"])
def maintenance_status(request):
    # Returns whether any maintenance window is currently active
    window = MaintenanceWindow.objects.filter(is_active=True).first()
    if window:
        data = {
            "maintenance_active": True,
            "name": window.name,
            "start_time": window.start_time.isoformat(),
            "end_time": window.end_time.isoformat(),
            "description": window.description,
        }
    else:
        data = {"maintenance_active": False}
    return Response(data)
