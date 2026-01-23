from rest_framework import serializers

from .models import Character


class CharacterSerializer(serializers.ModelSerializer):
    total_quests = serializers.IntegerField(read_only=True)

    class Meta:
        model = Character
        fields = [
            "id",
            "first_name",
            "last_name",
            "backstory",
            "sex",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "coins",
            "total_quests",
            "is_npc",
            "can_link",
        ]
        read_only_fields = [
            "id",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "coins",
            "total_quests",
            "is_npc",
            "can_link",
        ]
