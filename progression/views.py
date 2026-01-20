# progression/views.py
from datetime import timedelta
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.views import IsOwnerPlayer
from .models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    PlayerActivity,
    CharacterActivity,
    CharacterQuest,
    Project,
    Task,
)
from .serializers import (
    CategorySerializer,
    RoleSerializer,
    PlayerSkillSerializer,
    CharacterSkillSerializer,
    PlayerActivitySerializer,
    CharacterActivitySerializer,
    CharacterQuestSerializer,
    ProjectSerializer,
    TaskSerializer,
)
from .filters import (
    CategoryFilter,
    PlayerSkillFilter,
    PlayerActivityFilter,
    CharacterActivityFilter,
    ProjectFilter,
    TaskFilter,
)


#########################################
#####      Group viewsets
#########################################


class CategoryViewSet(viewsets.ModelViewSet):
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

    def get_queryset(self):
        return Category.objects.filter(player=self.request.user.player).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(player=self.request.user.player)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "character__name"]
    ordering_fields = ["created_at", "last_updated"]


#########################################
#####      Skill viewsets
#########################################


class PlayerSkillViewSet(viewsets.ModelViewSet):
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

    def get_queryset(self):
        return PlayerSkill.objects.filter(player=self.request.user.player).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(player=self.request.user.player)


class CharacterSkillViewSet(viewsets.ModelViewSet):
    queryset = CharacterSkill.objects.all()
    serializer_class = CharacterSkillSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "character__name"]
    ordering_fields = ["level", "created_at", "last_updated"]


#########################################
#####      TimeRecord viewsets
#########################################


class PlayerActivityViewSet(viewsets.ModelViewSet):
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

    def get_queryset(self):
        return PlayerActivity.objects.filter(
            profile=self.request.user.profile
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)

    def create(self, request, *args, **kwargs):
        serializer = self.serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(profile=request.user.profile)
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
        profile = request.user.profile
        activity = self.get_object()

        serializer = self.get_serializer(activity, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return latest activities (today’s or recent 5)
        activities = PlayerActivity.objects.filter(
            profile=profile, completed_at__date=timezone.now().date()
        ).order_by("-completed_at")
        if not activities.exists():
            activities = PlayerActivity.objects.filter(profile=profile).order_by(
                "-completed_at"
            )[:5]

        return Response(
            {
                "success": True,
                "message": "Activity submitted",
                "profile": ProfileSerializer(profile).data,
                "activities": PlayerActivitySerializer(activities, many=True).data,
            },
            status=status.HTTP_200_OK,
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


class CharacterActivityViewSet(viewsets.ModelViewSet):
    queryset = CharacterActivity.objects.all()
    serializer_class = CharacterActivitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CharacterActivityFilter
    search_fields = ["name", "description", "character__name"]
    ordering_fields = ["duration", "created_at", "last_updated", "scheduled_start"]

    def get_queryset(self):
        """
        Return CharacterActivity objects for the current user's active character.
        """
        character = self.request.user.player.current_character
        if not character:
            return CharacterActivity.objects.none()
        return CharacterActivity.objects.filter(character=character)

    @action(detail=False, methods=["get"])
    def current(self, request):
        character = request.user.player.current_character

        behaviour = getattr(character, "behaviour", None)
        if not behaviour:
            return Response(
                {
                    "current": None,
                    "message": "No behaviour!",
                }
            )

        # today = timezone.localdate()
        # yesterday = today - timedelta(days=1)

        # behaviour.generate_day(yesterday)
        # behaviour.generate_day(today)

        current = behaviour.sync_to_now()
        data = self.get_serializer(current).data if current else None
        return Response({"current": data})


class CharacterQuestViewSet(viewsets.ModelViewSet):
    queryset = CharacterQuest.objects.all()
    serializer_class = CharacterQuestSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "description", "character__name"]
    ordering_fields = ["duration", "target_duration", "created_at", "last_updated"]

    def get_queryset(self):
        """
        Return CharacterQuest objects for the current user's active character.
        """
        from character.models import PlayerCharacterLink

        player = self.request.user.player
        character = PlayerCharacterLink.get_character(player)
        if not character:
            return CharacterQuest.objects.none()
        return CharacterQuest.objects.filter(character=character)


#########################################
#####      Other viewsets
#########################################


class ProjectViewSet(viewsets.ModelViewSet):
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

    def get_queryset(self):
        return Project.objects.filter(player=self.request.user.player).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(player=self.request.user.player)


class TaskViewSet(viewsets.ModelViewSet):
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

    def get_queryset(self):
        return Task.objects.filter(player=self.request.user.player).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(player=self.request.user.player)
