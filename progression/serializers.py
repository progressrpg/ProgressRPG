from rest_framework import serializers

from .models import Activity, CharacterQuest, PlayerSkill
, CharacterSkill, Category, Role


class ActivitySerializer(serializers.ModelSerializer):
    created_at = serializers.DateTimeField(format="%Y-%m-%d %H:%M:%S")

    class Meta:
        model = Activity
        fields = ["id", "name", "duration", "created_at", "profile"]

class CharacterQuestSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CharacterQuest
        fields = "__all__"

class PlayerSkillSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PlayerSkill
        fields = "__all__"

class CharacterSkillSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = CharacterSkill
        fields = "__all__"

class CategorySerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Category
        fields = "__all__"

class PlayerSkillSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = PlayerSkill
        fields = "__all__"

