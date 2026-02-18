from rest_framework import serializers

from .models import Character


class CharacterSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    total_activities = serializers.IntegerField(read_only=True)
    current_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = Character
        fields = [
            "id",
            "first_name",
            "last_name",
            "backstory",
            "age",
            "sex",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "coins",
            "total_activities",
            "current_activity",
            "is_npc",
            "can_link",
        ]

        read_only_fields = fields

    def get_age(self, obj):
        return int(obj.get_age() // 365)

    def get_current_activity(self, obj):
        activity = obj.behaviour.get_current_activity()
        return activity.name if activity else None

    def __init__(self, *args, **kwargs):
        from .models import Character

        self.Meta.model = Character
        super().__init__(*args, **kwargs)
