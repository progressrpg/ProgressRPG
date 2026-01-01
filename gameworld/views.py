from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import JsonResponse

from users.models import Profile
from gameplay.models import QuestCompletion
from character.models import Character
from progression.models import PlayerActivity


@login_required
def get_game_statistics(request):
    if request.method == "GET":
        profiles = Profile.objects.all()
        profiles_num = len(profiles)
        highest_login_streak_ever = max(
            profile.login_streak_max for profile in profiles
        )
        highest_login_streak_current = max(profile.login_streak for profile in profiles)
        activities = PlayerActivity.objects.all()
        total_activity_num = len(activities)
        total_activity_time = sum(activity.duration for activity in activities)
        activities_num_average = total_activity_num / profiles_num
        activities_time_average = total_activity_time / profiles_num
        characters = Character.objects.all()
        characters_num = len(characters)
        questsCompleted = QuestCompletion.objects.all()
        unique_quests = set(qc.quest for qc in questsCompleted)
        total_quests = sum(qc.times_completed for qc in questsCompleted)
        quests_num_average = total_quests / characters_num
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid method"}, status=405)
