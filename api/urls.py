from dj_rest_auth import urls as auth_urls
from rest_framework_simplejwt.views import TokenVerifyView

from django.urls import path, include, register_converter
from rest_framework.routers import DefaultRouter
from django_channels_jwt.views import AsgiValidateTokenView

from .views import (
    CustomRegisterView,
    ConfirmEmailView,
    MeViewSet,
    FetchInfoAPIView,
    DownloadUserDataAPIView,
    DeleteAccountAPIView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
)

from character.views import CharacterViewSet
from gameplay.views import ActivityTimerViewSet
from progression.views import (
    PlayerActivityViewSet,
    CharacterActivityViewSet,
    CharacterQuestViewSet,
    PlayerSkillViewSet,
    CategoryViewSet,
    TaskViewSet,
)
from server_management.views import maintenance_status
from users.views import PlayerViewSet

from locations.views import PopulationCentreMapView


class KeyConverter:
    regex = "[^/]+"

    def to_python(self, value):
        from urllib.parse import unquote

        return unquote(value)

    def to_url(self, value):
        from urllib.parse import quote

        return quote(value)


register_converter(KeyConverter, "key")

router = DefaultRouter()
router.register(r"me", MeViewSet, basename="me")
router.register(r"player", PlayerViewSet, basename="player")
router.register(r"character", CharacterViewSet, basename="character")
router.register(r"skills", PlayerSkillViewSet, basename="skills")
router.register(r"tasks", TaskViewSet, basename="tasks")
router.register(r"player-activities", PlayerActivityViewSet, basename="playeractivity")
router.register(
    r"character-activities", CharacterActivityViewSet, basename="characteractivity"
)
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"character_quests", CharacterQuestViewSet, basename="characterquest")

router.register(r"quests", QuestViewSet, basename="quest")
router.register(r"activity_timers", ActivityTimerViewSet, basename="activitytimer")
router.register(r"quest_timers", QuestTimerViewSet, basename="questtimer")

urlpatterns = [
    # General urls
    path("", include(router.urls)),
    path("maintenance_status/", maintenance_status, name="maintenance_status"),
    path("fetch_info/", FetchInfoAPIView.as_view(), name="fetch_info"),
    # Auth urls
    path("ws_auth/", AsgiValidateTokenView.as_view(), name="ws_auth"),
    path("auth/", include(auth_urls)),
    path("auth/", include("users.urls")),
    path("auth/jwt/create/", CustomTokenObtainPairView.as_view(), name="jwt_create"),
    path("auth/jwt/refresh/", CustomTokenRefreshView.as_view(), name="jwt_refresh"),
    path("auth/jwt/verify/", TokenVerifyView.as_view(), name="jwt_verify"),
    # Registration urls
    path("auth/registration/", CustomRegisterView.as_view(), name="custom_register"),
    path(
        "auth/confirm_email/<key:key>/",
        ConfirmEmailView.as_view(),
        name="confirm_email",
    ),
    # Account urls
    path(
        "download_user_data/",
        DownloadUserDataAPIView.as_view(),
        name="api_download_user_data",
    ),
    path("delete_account/", DeleteAccountAPIView.as_view(), name="api_delete_account"),
    # Other urls
    path(
        "population-centres/<int:pk>/map/",
        PopulationCentreMapView.as_view(),
        name="populationcentre-map",
    ),
    # Other urls
    path(
        "population-centres/<int:pk>/map/",
        PopulationCentreMapView.as_view(),
        name="populationcentre-map",
    ),
]
