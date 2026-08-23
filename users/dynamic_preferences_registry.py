"""
User-level settings, registered through django-dynamic-preferences rather
than as fields on CustomUser. A new setting is a new class here - not a
migration - which is the whole point: earlier reminder categories would
each have wanted their own CustomUser column (or their own log model);
this gives every future one (see issue #805's settings page) a single
place to live, with defaults, admin visibility and per-user overrides for
free from the package.

Values are read via `user.preferences['<section>__<name>']` (dynamic
django-dynamic-preferences wires up `preferences` on the user model
through UserPreferencesConfig).
"""

from dynamic_preferences.preferences import Section
from dynamic_preferences.types import BooleanPreference
from dynamic_preferences.users.registries import user_preferences_registry

notifications = Section("notifications")


@user_preferences_registry.register
class InactivityReminderEmails(BooleanPreference):
    section = notifications
    name = "inactivity_reminder_emails"
    default = True
    verbose_name = "Inactivity reminder emails"
    help_text = (
        "Send a reminder email after 7 days with no recorded activity "
        "(see users.services.inactivity_reminder_service)."
    )
