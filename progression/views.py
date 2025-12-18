# progression/views.py
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.views import IsOwnerProfile
from .models import (
    Category,
    Role,
    PlayerSkill,
    CharacterSkill,
    Activity,
    CharacterQuest,
    Project,
    Task,
)
from .serializers import (
    CategorySerializer,
    RoleSerializer,
    PlayerSkillSerializer,
    CharacterSkillSerializer,
    ActivitySerializer,
    CharacterQuestSerializer,
    ProjectSerializer,
    TaskSerializer,
)
from .filters import (
    CategoryFilter,
    PlayerSkillFilter,
    ActivityFilter,
    ProjectFilter,
    TaskFilter,
)


#########################################
#####      Group viewsets
#########################################


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CategoryFilter
    search_fields = ["name", "description"]
    ordering_fields = ["created_at", "last_updated"]

    def get_queryset(self):
        return Category.objects.filter(profile=self.request.user.profile).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


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
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = PlayerSkillFilter
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["level", "created_at", "last_updated"]

    def get_queryset(self):
        return PlayerSkill.objects.filter(profile=self.request.user.profile).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


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


class ActivityViewSet(viewsets.ModelViewSet):
    serializer_class = ActivitySerializer
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ActivityFilter
    search_fields = [
        "name",
        "description",
        "skill__name",
        "project__name",
        "task__name",
    ]
    ordering_fields = ["duration", "created_at", "last_updated", "completed_at"]

    def get_queryset(self):
        return Activity.objects.filter(profile=self.request.user.profile).order_by(
            "-created_at"
        )

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
        activities = Activity.objects.filter(
            profile=profile, completed_at__date=timezone.now().date()
        ).order_by("-completed_at")
        if not activities.exists():
            activities = Activity.objects.filter(profile=profile).order_by(
                "-completed_at"
            )[:5]

        return Response(
            {
                "success": True,
                "message": "Activity submitted",
                "profile": ProfileSerializer(profile).data,
                "activities": ActivitySerializer(activities, many=True).data,
            },
            status=status.HTTP_200_OK,
        )


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

        profile = self.request.user.profile
        character = PlayerCharacterLink.get_character(profile)
        if not character:
            return CharacterQuest.objects.none()
        return CharacterQuest.objects.filter(character=character)


#########################################
#####      Other viewsets
#########################################


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = ProjectFilter
    search_fields = ["name", "description", "profile__name"]
    ordering_fields = ["created_at", "last_updated"]

    def get_queryset(self):
        return Project.objects.filter(profile=self.request.user.profile).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsOwnerProfile]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = TaskFilter
    search_fields = ["name", "description", "profile__name", "project__name"]
    ordering_fields = ["created_at", "last_updated"]

    def get_queryset(self):
        return Project.objects.filter(profile=self.request.user.profile).order_by(
            "-created_at"
        )

    def perform_create(self, serializer):
        serializer.save(profile=self.request.user.profile)
