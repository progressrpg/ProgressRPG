# All non-API Django template views have been removed.
# The frontend now uses REST API endpoints exclusively.

from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import MaintenanceWindow


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
