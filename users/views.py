# All non-API Django template views have been removed.
# The frontend now uses REST API endpoints exclusively.

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, mixins, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import logging

from .filters import ProfileFilter
from .models import Profile
from .serializers import ProfileSerializer

logger = logging.getLogger("django")


class ProfileViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    serializer_class = ProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Profile.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"])
    def me(self, request):
        profile = self.get_queryset().first()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
