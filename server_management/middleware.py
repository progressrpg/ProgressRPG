from django.shortcuts import redirect
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from server_management.models import MaintenanceWindow
from django.utils.timezone import now
from django.urls import resolve
from asgiref.sync import sync_to_async

BLOCKED_USER_AGENTS = ["bot", "crawler", "spider", "scraper", "wget", "curl"]


class AsyncBlockBotMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self._is_async = callable(get_response) and hasattr(get_response, "__await__")

    async def __call__(self, request):
        if request.path.startswith("/admin/"):
            return await sync_to_async(self.get_response)(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "").lower()
        if any(bot in user_agent for bot in BLOCKED_USER_AGENTS):
            return HttpResponseForbidden("Access denied.")
        return await self._get_response(request)

    async def _get_response(self, request):
        if self._is_async:
            return await self.get_response(request)
        else:
            return await sync_to_async(self.get_response)(request)


class AsyncMaintenanceModeMiddleware:
    """Middleware to restrict access during maintenance, allowing certain users/tests through."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._is_async = callable(get_response) and hasattr(get_response, "__await__")

    async def __call__(self, request):
        if request.path.startswith("/admin/"):
            return await sync_to_async(self.get_response)(request)
        active_window = await sync_to_async(
            lambda: MaintenanceWindow.objects.filter(is_active=True).first()
        )()

        user = getattr(request, "user", None)
        if active_window:
            if user and user.is_authenticated and user.is_staff:
                return await self._get_response(request)
            exempt_paths = [
                "/logout/",
                "/static/",
                "/admin/",
                "/healthcheck/",
                "/maintenance/",
                "/api/v1/maintenance_status/",
            ]
            if any(request.path.startswith(exempt) for exempt in exempt_paths):
                return await self._get_response(request)

            if request.path.startswith("/api/"):
                return JsonResponse({"detail": "Maintenance mode"}, status=503)
            return redirect("/maintenance/")
        else:
            return await self._get_response(request)

    async def _get_response(self, request):
        if self._is_async:
            return await self.get_response(request)
        else:
            return await sync_to_async(self.get_response)(request)
