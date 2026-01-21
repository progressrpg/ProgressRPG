from django.contrib.auth import get_user_model
from django.test import TestCase, Client, override_settings, tag
from django.urls import reverse
from unittest import skip
import logging

from users.models import Player
from users.tasks import send_email_to_users_task

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

    def test_character_assigned_on_player(self):
        """Test that a character is assigned to the user's player."""
        user = self.UserModel.objects.create_user(
            email="testuser1@example.com", password="testpassword123"
        )
        link = PlayerCharacterLink.objects.filter(player=user.player).first()
        character = link.character
        self.assertEqual(character, self.character)

    def test_player_defaults(self):
        """Test default values for a new player."""
        user = self.UserModel.objects.create_user(
            email="testuser2@example.com", password="testpassword123"
        )
        player = user.player
        self.assertEqual(player.onboarding_step, 0)
        self.assertEqual(player.total_time, 0)
        self.assertEqual(player.total_activities, 0)


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

    @skip("Need new character onboarding test")
    def test_onboarding_player(self):
        """Test the player creation step in onboarding."""
        url = reverse("create_profile")
        data = {"name": "Test name"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse("create_character")
        self.assertRedirects(response, expected_url)

        self.player.refresh_from_db()
        self.assertEqual(self.player.onboarding_step, 2)
        self.assertEqual(self.player.name, "Test name")

    @skip("Need new character onboarding test")
    def test_onboarding_character(self):
        """Test the character creation step in onboarding."""
        self.player.onboarding_step = 2
        self.player.save()

        url = reverse("create_character")
        data = {"character_name": "Test Character"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 302)
        expected_url = reverse("subscribe")
        self.assertRedirects(response, expected_url)

        self.player.refresh_from_db()
        self.assertEqual(self.player.onboarding_step, 3)
        self.assertEqual(self.player.character.first_name, "Test Character")

    @skip("Skipping as temporarily broken")
    def test_onboarding_subscribe(self):
        """Test the subscription step in onboarding."""
        self.player.onboarding_step = 3
        self.player.save()

        url = reverse("subscribe")
        response = self.client.post(url, {})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse("game")
        self.assertRedirects(response, expected_url)

        self.player.refresh_from_db()
        self.assertEqual(self.player.onboarding_step, 4)


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
        player.add_activity(10, 1)
        self.assertEqual(player.total_time, 10)
        self.assertEqual(player.total_activities, 1)

    def test_change_character(self):
        """Test changing the character linked to a player."""
        player = self.user.player
        player.change_character(self.character2)
        link = PlayerCharacterLink.objects.filter(player=player, is_active=True).first()
        self.assertEqual(link.character, self.character2)


@tag("fast")
class TestViews_LoggedOut(TestCase):
    def setUp(self):
        # urls
        self.index_url = reverse("index")
        self.player_url = reverse("player")
        self.editprofile_url = reverse("edit_profile")
        self.register_url = reverse("register")

    def test_profile_GET_loggedout(self):
        """Check redirect to login if user not logged in."""
        response = self.client.get(self.player_url)
        self.assertEqual(response.status_code, 302)

    def test_editprofile_GET_loggedout(self):
        """Check redirect to login if user not logged in."""
        response = self.client.get(self.editprofile_url)
        self.assertEqual(response.status_code, 302)

    def test_register_GET(self):
        """Check the register page is rendered successfully."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)


@override_settings(
    CELERY_TASK_ALWAYS_EAGER=True,  # run Celery tasks immediately, not via broker
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",  # in-memory email storage
)
class EmailTaskTest(TestCase):

    def test_send_email_task(self):
        emails = ["test@example.com"]
        subject = "Test Email"
        template_base = "emails/email_confirmation_message"
        context = {"user": {"email": "test@example.com"}}
        cc_admin = False

        # Run task synchronously
        send_email_to_users_task(
            emails=emails,
            subject=subject,
            template_base=template_base,
            context=context,
            cc_admin=cc_admin,
        )

        # Check that the email was sent
        from django.core.mail import outbox

        self.assertEqual(len(outbox), 1)  # one email was sent
        email = outbox[0]
        self.assertEqual(email.subject, subject)
        self.assertEqual(email.to, emails)
        self.assertIn("test@example.com", email.body)
