# All non-API Django template views have been removed.
# The frontend now uses REST API endpoints exclusively.

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging

from .models import Player
from .serializers import PlayerSerializer

logger = logging.getLogger("general")
logger_errors = logging.getLogger("errors")


class PlayerViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = PlayerSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return Player.objects.none()
        return Player.objects.filter(user=user)

    @action(detail=False, methods=["get"])
    def me(self, request):
        player = self.get_queryset().first()
        serializer = self.get_serializer(player)
        return Response(serializer.data)
