import os
from unittest.mock import patch

from django.test import SimpleTestCase

from progress_rpg.settings.utils import get_dev_email_backend


class DevEmailBackendSettingsTest(SimpleTestCase):
    def test_defaults_to_console_backend(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                get_dev_email_backend(),
                "django.core.mail.backends.console.EmailBackend",
            )

    def test_allows_explicit_override(self):
        with patch.dict(
            os.environ,
            {"EMAIL_BACKEND": "django.core.mail.backends.smtp.EmailBackend"},
            clear=True,
        ):
            self.assertEqual(
                get_dev_email_backend(),
                "django.core.mail.backends.smtp.EmailBackend",
            )
