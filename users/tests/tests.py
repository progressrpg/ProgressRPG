from django.contrib.auth import get_user_model
from django.core import mail
from django.http import HttpResponse
from django.test import TestCase, Client, override_settings, tag
from django.test.client import RequestFactory
from datetime import date, timedelta
from django.utils import timezone
from unittest.mock import patch
import logging
from types import SimpleNamespace

from allauth.core import context as allauth_context
from rest_framework.test import APIRequestFactory, force_authenticate

from api.views import MeViewSet
from api.serializers import CustomTokenObtainPairSerializer
from progress_rpg.middleware.timezone import UserTimezoneMiddleware
from users.adapters import CustomAccountAdapter
from users.serializers import PlayerSerializer
from users.models import Player, UserLogin
from progression.models import PlayerActivity
from users.tasks import send_email_to_users_task, send_rendered_email_task
from users.validators import (
    PLAYER_NAME_MAX_LENGTH,
    PLAYER_NAME_MIN_LENGTH,
    generate_default_player_name,
)

from character.models import Character, PlayerCharacterLink

logging.getLogger("general").setLevel(logging.CRITICAL)


class UserCreationTest(TestCase):
    def setUp(self):
        self.character = Character.objects.create(
            first_name="Jane", sex="Female", can_link=True
        )
        self.UserModel = get_user_model()

    def test_create_user(self):
        """Test that a user can be created successfully."""
        user = self.UserModel.objects.create_user(
            email="testuser@example.com", password="testpassword123"
        )
        self.assertEqual(user.email, "testuser@example.com")
        self.assertEqual(str(user.timezone), "UTC")
        self.assertTrue(user.check_password("testpassword123"))

        player = user.player
        self.assertTrue(isinstance(user.player, Player))
        self.assertEqual(user, user.player.user)
        self.assertEqual(user.player.xp, 0)

    def test_create_superuser(self):
        """Test that a superuser can be created successfully."""
        User = get_user_model()
        superuser = User.objects.create_superuser(
            email="admin@example.com", password="adminpassword123"
        )
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)

    def test_player_defaults(self):
        """Test default values for a new player."""
        user = self.UserModel.objects.create_user(
            email="testuser2@example.com", password="testpassword123"
        )
        player = user.player
        self.assertEqual(player.onboarding_step, 0)
        self.assertEqual(player.total_time, 0)
        self.assertEqual(player.total_activities, 0)
        self.assertRegex(player.name, r"^player_\d{8}$")

    def test_generated_player_names_are_unique(self):
        user1 = self.UserModel.objects.create_user(
            email="testuser3@example.com", password="testpassword123"
        )
        user2 = self.UserModel.objects.create_user(
            email="testuser4@example.com", password="testpassword123"
        )

        self.assertNotEqual(user1.player.name, user2.player.name)

    def test_generate_default_player_name_is_stable_for_a_player_id(self):
        generated_name = generate_default_player_name(12345)

        self.assertEqual(generated_name, generate_default_player_name(12345))
        self.assertRegex(generated_name, r"^player_\d{8}$")


class PlayerNameValidationTest(TestCase):
    def setUp(self):
        Character.objects.create(first_name="Jane", can_link=True)
        self.user = get_user_model().objects.create_user(
            email="player-name@example.com",
            password="testpassword123",
        )

    def test_player_serializer_accepts_trimmed_valid_name(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "  Red Fox-7  "},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "Red Fox-7")

    def test_player_serializer_accepts_leading_and_trailing_punctuation(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "-Red Fox-"},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "-Red Fox-")

    def test_player_serializer_rejects_invalid_characters(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "bad!!name"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")

    def test_player_serializer_rejects_too_short_name(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "ab"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")

    def test_player_serializer_rejects_repeated_separators(self):
        serializer = PlayerSerializer(
            self.user.player,
            data={"name": "Red--Fox"},
            partial=True,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(serializer.errors["name"][0], "Invalid player name.")


class OnboardingTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            email="testuser@example.com", password="testpassword123"
        )
        self.client.login(email="testuser@example.com", password="testpassword123")
        self.player = self.user.player

    def test_initial_onboarding(self):
        """Test that onboarding starts at step 0."""
        self.assertEqual(self.user.player.onboarding_step, 0)


@tag("fast")
class PlayerMethodsTest(TestCase):
    def setUp(self):
        self.character = Character.objects.create(first_name="Jane", can_link=True)
        self.character2 = Character.objects.create(first_name="John", can_link=True)
        User = get_user_model()
        self.user = User.objects.create_user(
            email="testuser1@example.com", password="testpassword123"
        )

    def test_player_add_activity(self):
        """Test adding activity to a player."""
        player = self.user.player
        activity = PlayerActivity.objects.create(
            player=player,
            name="Test activity",
            duration=10,
        )
        activity.complete()
        self.assertEqual(player.total_time, 10)
        self.assertEqual(player.total_activities, 1)

    def test_change_character(self):
        """Test changing the character linked to a player."""
        player = self.user.player
        player.change_character(self.character2)
        link = PlayerCharacterLink.objects.filter(player=player, is_active=True).first()
        self.assertEqual(link.character, self.character2)

    def test_current_character_returns_none_without_active_link(self):
        """Player.current_character should be None if there is no active link."""
        player = self.user.player
        PlayerCharacterLink.objects.filter(player=player, is_active=True).update(
            is_active=False
        )

        self.assertIsNone(player.current_character)


class UserLoginModelTest(TestCase):
    def setUp(self):
        Character.objects.create(first_name="Jane", can_link=True)
        self.user = get_user_model().objects.create_user(
            email="login-test@example.com",
            password="testpassword123",
        )

    def _create_login(self, days_ago):
        login = UserLogin.objects.create(user=self.user)
        timestamp = timezone.now() - timedelta(days=days_ago)
        UserLogin.objects.filter(pk=login.pk).update(timestamp=timestamp)
        return UserLogin.objects.get(pk=login.pk)

    def test_login_metrics_derive_from_userlogin_rows(self):
        self._create_login(3)
        self._create_login(1)
        self._create_login(0)

        self.assertEqual(self.user.days_logged_in, 3)
        self.assertEqual(self.user.current_login_streak, 2)
        self.assertEqual(self.user.max_login_streak, 2)
        self.assertEqual(self.user.total_login_events, 3)
        self.assertIsNotNone(self.user.last_recorded_login)


class JwtLoginTrackingTest(TestCase):
    def setUp(self):
        Character.objects.create(first_name="Jane", can_link=True)
        self.user = get_user_model().objects.create_user(
            email="jwt-login@example.com",
            password="testpassword123",
        )

    def test_token_serializer_creates_user_login_record(self):
        serializer = CustomTokenObtainPairSerializer(
            data={
                "email": "jwt-login@example.com",
                "password": "testpassword123",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(UserLogin.objects.filter(user=self.user).count(), 1)


class UserTimezoneApiTest(TestCase):
    def setUp(self):
        Character.objects.create(first_name="Jane", can_link=True)
        self.user = get_user_model().objects.create_user(
            email="timezone-api@example.com",
            password="testpassword123",
        )
        self.factory = APIRequestFactory()

    def test_me_settings_patch_updates_timezone(self):
        request = self.factory.patch(
            "/api/v1/me/settings/",
            {"timezone": "Europe/Paris"},
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = MeViewSet.as_view({"patch": "user_settings"})(request)

        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(str(self.user.timezone), "Europe/Paris")
        self.assertEqual(response.data["timezone"], "Europe/Paris")


class UserTimezoneMiddlewareTest(TestCase):
    def setUp(self):
        Character.objects.create(first_name="Jane", can_link=True)
        self.user = get_user_model().objects.create_user(
            email="timezone-middleware@example.com",
            password="testpassword123",
        )
        self.user.timezone = "Europe/Paris"
        self.user.save(update_fields=["timezone"])

    def tearDown(self):
        timezone.deactivate()

    def test_authenticated_request_activates_user_timezone(self):
        captured = {}

        def get_response(request):
            captured["timezone"] = str(timezone.get_current_timezone())
            return HttpResponse("ok")

        middleware = UserTimezoneMiddleware(get_response)
        request = RequestFactory().get("/")
        request.user = self.user

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(captured["timezone"], "Europe/Paris")


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,  # run Celery tasks immediately, not via broker
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",  # in-memory email storage
)
class EmailTaskTest(TestCase):

    def test_send_email_task(self):
        emails = ["test@example.com"]
        subject = "Test Email"
        template_base = "emails/email_confirmation_message"
        context = {
            "user": {"email": "test@example.com"},
            "activate_url": "https://example.com/confirm/test-token",
        }
        cc_admin = False

        send_email_to_users_task.apply(
            kwargs={
                "emails": emails,
                "subject": subject,
                "template_base": template_base,
                "context": context,
                "cc_admin": cc_admin,
            }
        )

        # Check that the email was sent
        self.assertEqual(len(mail.outbox), 1)  # one email was sent
        email = mail.outbox[0]
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, emails)
        self.assertIn("test@example.com", email.body)

    def test_send_rendered_email_task(self):
        send_rendered_email_task.apply(
            kwargs={
                "recipient_list": ["rendered@example.com"],
                "subject": "Rendered Email",
                "plain_message": "plain body",
                "html_message": "<p>html body</p>",
                "from_email": "Progress RPG <noreply@progressrpg.com>",
                "headers": {"X-Test": "1"},
            }
        )

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.subject, "Rendered Email")
        self.assertEqual(email.to, ["rendered@example.com"])
        self.assertEqual(email.body, "plain body")
        self.assertEqual(email.extra_headers["X-Test"], "1")
        alternative = email.alternatives[0]
        alternative_content = getattr(alternative, "content", alternative[0])
        self.assertEqual(alternative_content, "<p>html body</p>")


class CustomAccountAdapterTest(TestCase):
    def setUp(self):
        Character.objects.create(first_name="Jane", can_link=True)
        self.user = get_user_model().objects.create_user(
            email="adapter@example.com",
            password="testpassword123",
        )

    @patch("users.adapters.send_rendered_email_task.delay")
    def test_send_confirmation_mail_queues_email_task(self, mock_delay):
        request = RequestFactory().get("/")
        adapter = CustomAccountAdapter()
        emailconfirmation = SimpleNamespace(
            key="confirm123",
            email_address=SimpleNamespace(user=self.user, email=self.user.email),
        )

        with allauth_context.request_context(request):
            adapter.send_confirmation_mail(request, emailconfirmation, signup=True)

        mock_delay.assert_called_once()
        kwargs = mock_delay.call_args.kwargs
        self.assertEqual(kwargs["recipient_list"], [self.user.email])
        self.assertTrue(kwargs["subject"])
        self.assertIn("/confirm_email/confirm123", kwargs["plain_message"])


class AssignCharacterTest(TestCase):
    """Tests for assign_character_to_player function"""

    def setUp(self):
        from users.utils import assign_character_to_player
        from users.models import CustomUser

        # Create available NPCs
        self.npc1 = Character.objects.create(
            first_name="Available",
            last_name="NPC1",
            sex="Male",
            can_link=True,
        )
        self.npc2 = Character.objects.create(
            first_name="Available",
            last_name="NPC2",
            sex="Female",
            can_link=True,
        )

        # Create a user and player
        self.user = CustomUser.objects.create_user(
            email="testplayer@example.com", password="testpass123"
        )
        self.player = self.user.player

    def test_assign_character_to_player_success(self):
        """Test successful character assignment"""
        from users.utils import assign_character_to_player

        # Assign character
        character = assign_character_to_player(self.player)

        # Verify assignment
        self.assertIsNotNone(character)
        self.assertTrue(character in [self.npc1, self.npc2])

        # Verify link was created
        link = PlayerCharacterLink.objects.get(
            player=self.player, character=character, is_active=True
        )
        self.assertIsNotNone(link)

        # Verify character is no longer an NPC (has active link)
        self.assertFalse(character.is_npc)

    def test_assign_character_filters_correctly(self):
        """Test that assignment only considers valid NPCs"""
        from users.utils import assign_character_to_player

        # Create a character that's not linkable
        unlinkable = Character.objects.create(
            first_name="Unlinkable",
            last_name="Character",
            sex="Male",
            can_link=False,
        )

        # Create a dead character
        dead = Character.objects.create(
            first_name="Dead",
            last_name="Character",
            sex="Female",
            can_link=True,
            death_date=date.today(),
        )

        from users.models import CustomUser

        user2 = CustomUser.objects.create_user(
            email="user2@example.com", password="pass"
        )
        PlayerCharacterLink.assign_character(player=user2.player, character=self.npc1)

        # Assign character to our player
        character = assign_character_to_player(self.player)

        # Should get npc2 (only valid option)
        self.assertEqual(character, self.npc2)

        # Unlinkable and dead characters should not be assigned
        self.assertNotEqual(character, unlinkable)
        self.assertNotEqual(character, dead)

    def test_assign_character_no_available_npcs(self):
        """Test assignment when no NPCs are available"""
        from users.utils import assign_character_to_player

        from users.models import CustomUser

        user1 = CustomUser.objects.create_user(email="user1@test.com", password="pass")
        user2 = CustomUser.objects.create_user(email="user2@test.com", password="pass")
        PlayerCharacterLink.assign_character(player=user1.player, character=self.npc1)
        PlayerCharacterLink.assign_character(player=user2.player, character=self.npc2)

        # Try to assign to our player (which already has its auto-assigned character unlinked)
        character = assign_character_to_player(self.player)

        # Should return None - no available characters
        self.assertIsNone(character)
