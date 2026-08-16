# progression/views.py
from typing import TYPE_CHECKING
from datetime import timedelta
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

if TYPE_CHECKING:
    from rest_framework.views import APIView as _RequestMixinBase
else:
    _RequestMixinBase = object

from api.views import IsAdminOrReadOnly, IsOwnerPlayer
from .models import (
    Category,
    Role,
    SkillGroup,
    SkillDefinition,
    CharacterRole,
    PlayerSkill,
    CharacterSkill,
    Activity,
    SuggestedActivity,
    PlayerActivity,
    ActivityDefinition,
    CharacterActivity,
    Project,
    Task,
    Note,
)
from .serializers import (
    CategorySerializer,
    RoleSerializer,
    SkillGroupSerializer,
    SkillDefinitionSerializer,
    CharacterRoleSerializer,
    PlayerSkillSerializer,
    CharacterSkillSerializer,
    ActivitySerializer,
    SuggestedActivitySerializer,
    PlayerActivitySerializer,
    OfflineActivityLogSerializer,
    ActivityDefinitionSerializer,
    CharacterActivitySerializer,
    ProjectSerializer,
    TaskSerializer,
    NoteSerializer,
)
from .services import log_offline_activity
from .filters import (
    CategoryFilter,
    PlayerSkillFilter,
    PlayerActivityFilter,
    CharacterActivityFilter,
    ProjectFilter,
    TaskFilter,
    NoteFilter,
)

#########################################
#####      Group viewsets
#########################################


def _request_player_or_none(request):
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return getattr(user, "player", None)


class PlayerScopedQuerysetMixin(_RequestMixinBase):
    """Scopes a viewset's queryset to the requesting player's own records and
    creates new records under that same player. Set `model` (and optionally
    `ordering`, default "-created_at") on the viewset.
    """

    model: type[models.Model] | None = None
    ordering = "-created_at"

    def get_queryset(self):
        assert self.model is not None
        player = _request_player_or_none(self.request)
        if not player:
            return self.model._default_manager.none()
        qs = self.model._default_manager.filter(player=player)
        return qs.order_by(self.ordering) if self.ordering else qs

    def perform_create(self, serializer):
        player = _request_player_or_none(self.request)
        serializer.save(player=player)


class CategoryViewSet(PlayerScopedQuerysetMixin, viewsets.ModelViewSet):
    model = Category
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsOwnerPlayer]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CategoryFilter
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "last_updated"]


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "last_updated"]


class SkillGroupViewSet(viewsets.ModelViewSet):
    queryset = SkillGroup.objects.all()
    serializer_class = SkillGroupSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "role__name"]
    ordering_fields = ["created_at", "last_updated"]


class SkillDefinitionViewSet(viewsets.ModelViewSet):
    queryset = SkillDefinition.objects.all()
    serializer_class = SkillDefinitionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "role__name"]
    ordering_fields = ["created_at", "last_updated"]


class CharacterRoleViewSet(viewsets.ModelViewSet):
    queryset = CharacterRole.objects.all()
    serializer_class = CharacterRoleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["character__name", "role__name"]
    ordering_fields = ["assigned_at"]


#########################################
#####      Skill viewsets
#########################################


class PlayerSkillViewSet(PlayerScopedQuerysetMixin, viewsets.ModelViewSet):
    model = PlayerSkill
    serializer_class = PlayerSkillSerializer
    permission_classes = [IsAuthenticated, IsOwnerPlayer]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PlayerSkillFilter
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["level", "created_at", "last_updated"]


class CharacterSkillViewSet(viewsets.ModelViewSet):
    queryset = CharacterSkill.objects.all()
    serializer_class = CharacterSkillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["skill_definition__name", "character__name"]
    ordering_fields = ["created_at", "last_updated"]


#########################################
#####      Activity viewsets
#########################################


class ActivityViewSet(PlayerScopedQuerysetMixin, viewsets.ModelViewSet):
    model = Activity
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated, IsOwnerPlayer]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "last_updated"]


class SuggestedActivityViewSet(viewsets.ModelViewSet):
    queryset = SuggestedActivity.objects.all()
    serializer_class = SuggestedActivitySerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description"]
    ordering_fields = ["name", "created_at", "last_updated"]


#########################################
#####      TimeRecord viewsets
#########################################


class PlayerActivityViewSet(PlayerScopedQuerysetMixin, viewsets.ModelViewSet):
    model = PlayerActivity
    serializer_class = PlayerActivitySerializer
    permission_classes = [IsAuthenticated, IsOwnerPlayer]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PlayerActivityFilter
    search_fields = [
        "name",
        "description",
        "skill__name",
        "project__name",
        "task__name",
    ]
    ordering_fields = ["duration", "created_at", "last_updated", "completed_at"]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(player=request.user.player)
        return Response(
            {
                "success": True,
                "message": "Activity created",
                "activity": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="submit",
        permission_classes=[IsAuthenticated],
    )
    def submit(self, request, pk=None):
        player = request.user.player
        activity = self.get_object()

        serializer = self.get_serializer(activity, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return latest activities (today’s or recent 5)
        activities = PlayerActivity.objects.filter(
            player=player, completed_at__date=timezone.now().date()
        ).order_by("-completed_at")
        if not activities.exists():
            activities = PlayerActivity.objects.filter(player=player).order_by(
                "-completed_at"
            )[:5]
        from users.serializers import PlayerSerializer

        return Response(
            {
                "success": True,
                "message": "Activity submitted",
                "player": PlayerSerializer(player).data,
                "activities": PlayerActivitySerializer(activities, many=True).data,
            },
            status=status.HTTP_200_OK,
        )

    @action(
        detail=False,
        methods=["post"],
        url_path="log_offline",
        permission_classes=[IsAuthenticated],
    )
    def log_offline(self, request):
        player = request.user.player
        serializer = OfflineActivityLogSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        task = data.get("task")
        name = data.get("name") or task.name

        try:
            result = log_offline_activity(
                player,
                name=name,
                description=data.get("description", ""),
                skill=data.get("skill"),
                task=task,
                started_at=data["started_at"],
                completed_at=data["completed_at"],
            )
        except DjangoValidationError as exc:
            return Response(
                {"success": False, "message": "; ".join(exc.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "success": True,
                "message": "Activity logged",
                "activity": PlayerActivitySerializer(result.activity).data,
                "xp_gained": result.reward_summary["xp_gained"],
                "xp_eligible_seconds": result.xp_eligible_seconds,
                "level_ups": result.level_ups,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["patch"])
    def change_skill(self, request, pk=None):
        activity = self.get_object()
        skill_id = request.data.get("skill_id")
        # validate + assign skill
        return Response({"success": True})

    @action(detail=True, methods=["patch"])
    def change_task(self, request, pk=None):
        activity = self.get_object()
        task_id = request.data.get("task_id")
        # validate + assign task
        return Response({"success": True})


class CurrentCharacterScopedQuerysetMixin(_RequestMixinBase):
    """Scopes a viewset's queryset to the requesting player's current
    character's own records. Set `model` on the viewset.
    """

    model: type[models.Model] | None = None

    def get_queryset(self):
        assert self.model is not None
        player = _request_player_or_none(self.request)
        if not player:
            return self.model._default_manager.none()

        character = player.current_character
        if not character:
            return self.model._default_manager.none()
        return self.model._default_manager.filter(character=character)


class ActivityDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ActivityDefinition.objects.all()
    serializer_class = ActivityDefinitionSerializer
    permission_classes = [IsAuthenticated, IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "kind"]
    ordering_fields = ["created_at", "last_updated"]


class CharacterActivityViewSet(
    CurrentCharacterScopedQuerysetMixin, viewsets.ModelViewSet
):
    model = CharacterActivity
    serializer_class = CharacterActivitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CharacterActivityFilter
    search_fields = ["activity_definition__name", "character__name"]
    ordering_fields = [
        "duration",
        "created_at",
        "last_updated",
        "scheduled_start",
        "completed_at",
    ]

    @action(detail=False, methods=["get"])
    def current(self, request):
        character = request.user.player.current_character

        if not character:
            return Response({"current": None, "message": "No active character."})

        behaviour = getattr(character, "behaviour", None)
        if not behaviour:
            return Response(
                {
                    "current": None,
                    "message": "No behaviour!",
                }
            )

        current = behaviour.sync_to_now()
        data = self.get_serializer(current).data if current else None
        return Response({"current": data})


#########################################
#####      Other viewsets
#########################################


class ProjectViewSet(PlayerScopedQuerysetMixin, viewsets.ModelViewSet):
    model = Project
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwnerPlayer]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProjectFilter
    search_fields = ["name", "description", "player__name"]
    ordering_fields = ["created_at", "last_updated", "completed_at"]


class TaskViewSet(PlayerScopedQuerysetMixin, viewsets.ModelViewSet):
    model = Task
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsOwnerPlayer]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = TaskFilter
    search_fields = ["name", "description", "player__name", "project__name"]
    ordering_fields = ["created_at", "last_updated", "completed_at"]

    def partial_update(self, request, *args, **kwargs):
        from core.models import GameSettings

        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        is_complete = serializer.validated_data.get("is_complete", instance.is_complete)
        is_newly_completing = (
            is_complete is True
            and not instance.is_complete
            and instance.first_completed_at is None
        )

        completion_xp_gained = 0
        level_ups = []

        if is_newly_completing:
            bonus_xp = int(GameSettings.current().task_completion_xp)
            serializer.save(first_completed_at=timezone.now())
            level_ups = request.user.player.add_activity(xp=bonus_xp)
            completion_xp_gained = bonus_xp
        else:
            serializer.save()

        return Response(
            {
                **serializer.data,
                "completion_xp_gained": completion_xp_gained,
                "level_ups": level_ups,
            }
        )


class NoteViewSet(PlayerScopedQuerysetMixin, viewsets.ModelViewSet):
    model = Note
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated, IsOwnerPlayer]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = NoteFilter
    search_fields = ["title", "body", "task__name"]
    ordering_fields = ["created_at", "last_updated"]
