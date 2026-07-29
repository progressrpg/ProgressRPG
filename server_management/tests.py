from unittest.mock import patch

from django.test import TestCase

from server_management.admin import FeatureFlagForm
from server_management.models import FeatureFlag

_FAKE_FEATURE_FLAGS_TS = """
const featureFlags = {
  activityList: ['all'],
  tasksFeature: ['testers'],
  categoriesFeature: [],
  skillsFeature: [],
  projectsFeature: [],
};
"""


@patch("server_management.admin._FEATURE_FLAGS_TS")
class FeatureFlagFormKeyChoicesTests(TestCase):
    def test_excludes_keys_already_created(self, mock_path):
        mock_path.read_text.return_value = _FAKE_FEATURE_FLAGS_TS
        FeatureFlag.objects.create(key="tasksFeature", access_groups=["testers"])

        form = FeatureFlagForm()

        choice_keys = [key for key, _ in form.fields["key"].choices]
        self.assertNotIn("tasksFeature", choice_keys)
        self.assertIn("activityList", choice_keys)
        self.assertIn("categoriesFeature", choice_keys)

    def test_editing_existing_flag_keeps_its_own_key_selectable(self, mock_path):
        mock_path.read_text.return_value = _FAKE_FEATURE_FLAGS_TS
        flag = FeatureFlag.objects.create(key="tasksFeature", access_groups=["testers"])
        FeatureFlag.objects.create(key="activityList", access_groups=["all"])

        form = FeatureFlagForm(instance=flag)

        choice_keys = [key for key, _ in form.fields["key"].choices]
        self.assertIn("tasksFeature", choice_keys)
        self.assertNotIn("activityList", choice_keys)
