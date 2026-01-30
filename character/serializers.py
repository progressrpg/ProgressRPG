from rest_framework import serializers

from .models import Character


class CharacterSerializer(serializers.ModelSerializer):
    total_activities = serializers.IntegerField(read_only=True)

    population_centre_id = serializers.PrimaryKeyRelatedField(
        source="population_centre", read_only=True
    )
    location = serializers.SerializerMethodField()

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
            "total_activities",
            "is_npc",
            "can_link",
            "population_centre_id",
            "location",
            "current_node",
            "target_node",
        ]
        read_only_fields = [
            "id",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "coins",
            "total_activities",
            "can_link",
            "population_centre_id",
            "location",
            "current_node",
            "target_node",
        ]
        read_only_fields = fields

    def get_location(self, obj):
        # obj must have x and y attributes, or replace with obj.position.x / obj.position.y
        if not obj.current_node:
            return None

        return {
            "type": "Point",
            "coordinates": [
                obj.current_node.location.x,
                obj.current_node.location.y,
            ],  # adjust to your model
        }

    def __init__(self, *args, **kwargs):
        from .models import Character

        self.Meta.model = Character
        super().__init__(*args, **kwargs)
