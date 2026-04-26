from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
import logging

from .models import Quest

from .serializers import (
    QuestSerializer,
    ActivityTimerSerializer,
    QuestTimerSerializer,
)
from .filters import QuestFilter
from .utils import check_quest_eligibility

from character.models import PlayerCharacterLink

from progression.models import Task

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


# All non-API Django template views have been removed.
# The frontend now uses REST API endpoints exclusively.


class QuestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API endpoint for Quest instances.
    """

    serializer_class = QuestSerializer
    permission_classes = [IsAuthenticated]
    queryset = Quest.objects.all().order_by("id")

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = QuestFilter
    search_fields = ["name", "description", "intro_text", "outro_text"]
    ordering_fields = ["id", "name"]

    @action(detail=False, methods=["get"])
    def eligible(self, request):
        # check_quest_eligibility is not called at this time.
        # The character link and eligibility logic below is kept for future use:
        #
        #   player = request.user.player
        #   try:
        #       character = PlayerCharacterLink.get_character(player)
        #   except ValueError as e:
        #       logger.warning(
        #           "Failed to get character for player %s: %s",
        #           player.id if hasattr(player, "id") else player,
        #           e,
        #       )
        #       return Response(
        #           {"error": "Unable to determine eligible quests for your character."},
        #           status=400,
        #       )
        #   eligible_quests = check_quest_eligibility(character, player)
        #   serializer = self.get_serializer(eligible_quests, many=True)
        #   return Response({"eligible_quests": serializer.data})

        return Response({"eligible_quests": []})


class BaseTimerViewSet(viewsets.ViewSet):
    """
    Abstract base class for timer viewsets. Enforces IsAuthenticated.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = None

    def serialize(self, timer):
        return self.serializer_class(timer).data

    @action(detail=False, methods=["post"])
    def start(self, request):
        timer = self.get_timer(request)
        timer.start()
        return Response(self.serialize(timer))

    @action(detail=False, methods=["post"])
    def pause(self, request):
        timer = self.get_timer(request)
        timer.pause()
        return Response(self.serialize(timer))

    @action(detail=False, methods=["post"])
    def reset(self, request):
        timer = self.get_timer(request)
        timer.reset()
        return Response(self.serialize(timer))

    @action(detail=False, methods=["post"])
    def complete(self, request):
        timer = self.get_timer(request)
        print("datadata:", request.data)
        name = request.data.get("activityName")

        result = timer.complete(newName=name)
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
    def complete(self, request):
        timer = self.get_timer(request)
        name = request.data.get("activityName")

        completion = timer.complete(newName=name)

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
        return Response({"success": True, "activity_timer": self.serialize(updated)})


class QuestTimerViewSet(BaseTimerViewSet):
    serializer_class = QuestTimerSerializer
    permission_classes = [IsAuthenticated]

    def get_timer(self, request):
        character = request.user.player.current_character
        if character is None:
            raise NotFound(
                "No active character found. Please link a character to access quest timers."
            )
        timer = character.quest_timer
        if timer is None:
            raise NotFound(f"Quest timer not found")
        return timer

    @action(detail=False, methods=["post"])
    def change_quest(self, request):
        timer = self.get_timer(request)

        if not request.data.get("quest_id"):
            return Response(
                {"error": "quest_id is required."}, status=status.HTTP_400_BAD_REQUEST
            )

        quest_id = request.data.get("quest_id")
        duration = request.data.get("duration")
        try:
            duration = int(request.data.get("duration"))
        except (TypeError, ValueError):
            return Response(
                {"error": "Duration must be an integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        quest = get_object_or_404(Quest, id=quest_id)
        timer.change_quest(quest, duration)
        timer.refresh_from_db()

        return Response({"success": True, "quest_timer": self.serialize(timer)})
