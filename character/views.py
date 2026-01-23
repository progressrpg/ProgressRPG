from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
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
    queryset = Character.objects.all()

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = CharacterFilter
    search_fields = ["first_name", "last_name", "backstory"]
    ordering_fields = ["level", "xp", "coins"]

    def get_queryset(self):
        # Later you might filter by proximity or visibility
        # location = self.request.user.player.location
        # return super().get_queryset().filter(location__near=location)
        return super().get_queryset()
