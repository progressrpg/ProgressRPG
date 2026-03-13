from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

import character
from .models import Character
from .serializers import CharacterSerializer
from .filters import CharacterFilter


class CharacterViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Viewset for listing and retrieving characters.
    Characters can be browsed by authenticated users — for example,
    to view their history or find nearby players.

    Modifications to characters should happen only via gameplay endpoints
    (e.g. quest completion, XP gain), not through direct update.
    """

    serializer_class = CharacterSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CharacterFilter
    search_fields = ["first_name", "last_name", "backstory"]
    ordering_fields = ["level", "xp"]

    def get_queryset(self):
        user = getattr(self.request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return Character.objects.none()
        player = getattr(user, "player", None)
        if not player:
            return Character.objects.none()
        character = player.current_character
        if not character:
            return Character.objects.none()
        return Character.objects.filter(id=character.id)
