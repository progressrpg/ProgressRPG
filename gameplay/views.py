from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import BaseSerializer
import logging

from .serializers import ActivityTimerSerializer
from .utils import broadcast_activity_timer

from progression.models import Task

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


# All non-API Django template views have been removed.
# The frontend now uses REST API endpoints exclusively.


class BaseTimerViewSet(viewsets.ViewSet):
    """
    Abstract base class for timer viewsets. Enforces IsAuthenticated.
    """

    permission_classes = [IsAuthenticated]
    serializer_class: type[BaseSerializer] | None = None

    def get_timer(self, request):
        raise NotImplementedError

    def serialize(self, timer):
        assert self.serializer_class is not None
        return self.serializer_class(timer).data

    def broadcast_timer_update(self, timer):
        broadcast_activity_timer(timer)

    @action(detail=False, methods=["post"])
    def start(self, request):
        timer = self.get_timer(request)
        timer.start()
        self.broadcast_timer_update(timer)
        return Response(self.serialize(timer))

    @action(detail=False, methods=["post"])
    def pause(self, request):
        timer = self.get_timer(request)
        timer.pause()
        self.broadcast_timer_update(timer)
        return Response(self.serialize(timer))

    @action(detail=False, methods=["post"])
    def reset(self, request):
        timer = self.get_timer(request)
        timer.reset()
        self.broadcast_timer_update(timer)
        return Response(self.serialize(timer))

    @action(detail=False, methods=["post"])
    def complete(self, request):
        timer = self.get_timer(request)
        name = request.data.get("activityName")

        timer.complete(newName=name)
        self.broadcast_timer_update(timer)
        return Response(self.serialize(timer))


class ActivityTimerViewSet(BaseTimerViewSet):
    serializer_class = ActivityTimerSerializer
    permission_classes = [IsAuthenticated]

    def get_timer(self, request):
        timer = request.user.player.activity_timer
        if timer is None:
            raise NotFound(f"Activity timer not found")
        return timer

    @action(detail=False, methods=["post"])
    def complete(self, request):  # type: ignore[override]
        timer = self.get_timer(request)
        name = request.data.get("activityName")
        raw_elapsed_seconds = request.data.get("elapsedSeconds")
        raw_source = request.data.get("source")

        try:
            client_elapsed_seconds = int(raw_elapsed_seconds)
        except (TypeError, ValueError):
            client_elapsed_seconds = None

        completion_source = raw_source if raw_source in {"auto", "manual"} else "manual"

        completion = timer.complete(
            newName=name,
            client_elapsed_seconds=client_elapsed_seconds,
            completion_source=completion_source,
        )
        self.broadcast_timer_update(timer)

        return Response({"activity_timer": self.serialize(timer), **completion})

    @action(detail=False, methods=["post"])
    def set_activity(self, request):
        timer = self.get_timer(request)

        name = request.data.get("activityName")
        if not name:
            name = ""

        task_id = request.data.get("task_id")
        task = None
        if task_id:
            task = get_object_or_404(Task, pk=task_id, player=request.user.player)

        updated = timer.new_activity(name=name, task=task)
        updated.refresh_from_db()
        self.broadcast_timer_update(updated)
        return Response({"success": True, "activity_timer": self.serialize(updated)})

    @action(detail=False, methods=["post"])
    def label_activity(self, request):
        """
        Rename (and optionally re-link to a task) the activity already
        assigned to a running/waiting timer, in place — unlike
        set_activity, this does not reset elapsed time or status.
        """
        timer = self.get_timer(request)

        if timer.status not in ("active", "waiting") or not timer.activity:
            return Response(
                {"error": "No running timer to label."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        name = request.data.get("activityName")
        if not name:
            name = ""

        task_id = request.data.get("task_id")
        if task_id:
            task = get_object_or_404(Task, pk=task_id, player=request.user.player)
            timer.change_task(task)

        timer.rename_activity(name)
        self.broadcast_timer_update(timer)

        return Response({"success": True, "activity_timer": self.serialize(timer)})
