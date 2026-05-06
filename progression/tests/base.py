from django.contrib.auth import get_user_model
from django.test import TestCase

from character.models import Character
from users.models import Player

import logging

User = get_user_model()

logger = logging.getLogger("general")


class BaseTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="test@test.com", password="pass")
        self.character = Character.objects.create(
            name="Test Character",
        )
        self.player, _ = Player.objects.get_or_create(
            user=self.user,
        )
        self.player.name = "Test Player"
