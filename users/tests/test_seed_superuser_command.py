import os
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase


class SeedSuperuserCommandTests(TestCase):
    """seed_superuser creates (or reuses) the dev superuser and always
    ensures it's in the "Testers" group (see core.models.FeatureFlag)."""

    def setUp(self):
        self.user_model = get_user_model()

    def _run(self, env):
        """Runs the command with `env` applied over the process environment.
        A value of None unsets that var for the duration of the call —
        needed since DJANGO_SUPERUSER_PASSWORD is normally already set
        (compose/.env) in the environment tests run in.
        """
        old = {key: os.environ.get(key) for key in env}
        for key, value in env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        try:
            stdout = StringIO()
            call_command("seed_superuser", stdout=stdout)
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        return stdout

    def test_creates_superuser_and_adds_to_testers_group(self):
        stdout = self._run(
            {
                "DJANGO_SUPERUSER_EMAIL": "dev-super@example.com",
                "DJANGO_SUPERUSER_PASSWORD": "correcthorsebatterystaple",
            }
        )

        user = self.user_model.objects.get(email="dev-super@example.com")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.groups.filter(name="Testers").exists())
        self.assertIn("created successfully", stdout.getvalue())

    def test_existing_superuser_still_gets_added_to_testers_group(self):
        user = self.user_model.objects.create_superuser(
            email="dev-super@example.com", password="old-password"
        )
        self.assertFalse(user.groups.filter(name="Testers").exists())

        self._run(
            {
                "DJANGO_SUPERUSER_EMAIL": "dev-super@example.com",
                "DJANGO_SUPERUSER_PASSWORD": "correcthorsebatterystaple",
            }
        )

        user.refresh_from_db()
        self.assertTrue(user.groups.filter(name="Testers").exists())

    def test_reuses_existing_testers_group_instead_of_duplicating(self):
        existing_group = Group.objects.create(name="Testers")

        self._run(
            {
                "DJANGO_SUPERUSER_EMAIL": "dev-super@example.com",
                "DJANGO_SUPERUSER_PASSWORD": "correcthorsebatterystaple",
            }
        )

        self.assertEqual(Group.objects.filter(name="Testers").count(), 1)
        user = self.user_model.objects.get(email="dev-super@example.com")
        self.assertIn(existing_group, user.groups.all())

    def test_no_op_when_password_env_var_missing(self):
        self._run(
            {
                "DJANGO_SUPERUSER_EMAIL": "dev-super@example.com",
                "DJANGO_SUPERUSER_PASSWORD": None,
            }
        )

        self.assertFalse(
            self.user_model.objects.filter(email="dev-super@example.com").exists()
        )
