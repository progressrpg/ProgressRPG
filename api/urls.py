from dj_rest_auth import urls as auth_urls
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

from django.urls import path, include, register_converter
from rest_framework.routers import DefaultRouter
from django_channels_jwt.views import AsgiValidateTokenView

from .views import (
    me_view,
    maintenance_status,
    CustomRegisterView,
    ConfirmEmailView,
    OnboardingViewSet,
    FetchInfoAPIView,
    ActivityTimerViewSet,
    QuestTimerViewSet,
    DownloadUserDataAPIView,
    DeleteAccountAPIView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
)

from character.views import CharacterViewSet
from gameplay.views import QuestViewSet
from progression.views import (
    ActivityViewSet,
    CharacterQuestViewSet,
    PlayerSkillViewSet,
    CategoryViewSet,
)
from users.views import ProfileViewSet


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
router.register(r"profile", ProfileViewSet, basename="profile")
router.register(r"character", CharacterViewSet, basename="character")
router.register(r"skills", PlayerSkillViewSet, basename="skills")
router.register(r"activities", ActivityViewSet, basename="activity")
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"character_quests", CharacterQuestViewSet, basename="characterquest")

router.register(r"quests", QuestViewSet, basename="quest")
router.register(r"activity_timers", ActivityTimerViewSet, basename="activitytimer")
router.register(r"quest_timers", QuestTimerViewSet, basename="questtimer")
router.register(r"onboarding", OnboardingViewSet, basename="onboarding")


urlpatterns = [
    # General urls
    path("", include(router.urls)),
    path("me/", me_view, name="me"),
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
]
