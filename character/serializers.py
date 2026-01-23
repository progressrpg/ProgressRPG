from rest_framework import serializers


class CharacterSerializer(serializers.ModelSerializer):
    population_centre_id = serializers.PrimaryKeyRelatedField(
        source="population_centre", read_only=True
    )
    location = serializers.SerializerMethodField()  # use method

    class Meta:
        model = None
        fields = [
            "id",
            "name",
            "xp",
            "xp_next_level",
            "xp_modifier",
            "level",
            "total_quests",
            "population_centre_id",
            "location",  # this is calculated with a method!
            "current_node",
            "target_node",
        ]
        read_only_fields = fields

    def get_location(self, obj):
        # obj must have x and y attributes, or replace with obj.position.x / obj.position.y
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
