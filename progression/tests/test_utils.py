from django.test import TestCase

from progression.models import CharacterQuest
from progression.utils import copy_quest
from character.models import Character
from gameplay.models import Quest


class UtilityCopyQuest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.character = Character.objects.create(name="Bob", sex="Male")
        cls.quest = Quest.objects.create(name="Test quest")

    def test_copy_quest(self):
        cq = copy_quest(self.character, self.quest)
        self.assertIsInstance(cq, CharacterQuest)
