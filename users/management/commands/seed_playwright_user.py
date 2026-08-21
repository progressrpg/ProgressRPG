import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import TutorialStep
from users.services.registration_services import ensure_player_setup_for_user


DEFAULT_PLAYWRIGHT_EMAIL = "playwright@example.com"
DEFAULT_PLAYWRIGHT_PASSWORD = "correcthorsebatterystaple"
DEFAULT_PLAYWRIGHT_PLAYER_NAME = "Playwright Hero"

# One dedicated user per (timer-touching Playwright spec file, project) -
# keep in sync with TIMER_SUITE_SLUGS/PROJECT_NAMES in
# frontend/playwright/testUser.ts. ActivityTimer is a OneToOneField per
# player, broadcast over a single WebSocket channel per player, so runs
# sharing a user race each other's Start/Stop/label calls - and Playwright
# runs each spec file once per matching project (chromium/firefox/webkit,
# plus a11y for the two a11y-named files) concurrently, so the user has to
# be dedicated per (slug, project) pair, not just per spec file.
PLAYWRIGHT_SUITE_SLUGS = [
    "a11y-pages",
    "a11y-tasks",
    "accessibility",
    "auth-logout",
    "tasks-core-loop",
    "tasks-projects",
    "timer",
    "unified-timer-home",
    "smoke-pages",
]
PLAYWRIGHT_PROJECT_NAMES = ["chromium", "firefox", "webkit", "a11y"]


class Command(BaseCommand):
    help = "Create or reset the dedicated Playwright E2E user(s)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default=os.getenv("PLAYWRIGHT_TEST_EMAIL", DEFAULT_PLAYWRIGHT_EMAIL),
            help="Email for the Playwright test user (base email when --all is passed).",
        )
        parser.add_argument(
            "--password",
            default=os.getenv("PLAYWRIGHT_TEST_PASSWORD", DEFAULT_PLAYWRIGHT_PASSWORD),
            help="Password for the Playwright test user(s).",
        )
        parser.add_argument(
            "--player-name",
            default=os.getenv(
                "PLAYWRIGHT_TEST_PLAYER_NAME", DEFAULT_PLAYWRIGHT_PLAYER_NAME
            ),
            help="Display name for the Playwright player profile (base name when --all is passed).",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help=(
                "Seed the base user plus one dedicated plus-addressed user per "
                "Playwright spec suite, all in this one process/container."
            ),
        )

    def handle(self, *args, **options):
        password = options["password"]
        if not password:
            raise CommandError("A Playwright test password is required.")

        if options["all"]:
            local, _, domain = options["email"].partition("@")
            self._seed_one(options["email"], password, options["player_name"])
            for slug in PLAYWRIGHT_SUITE_SLUGS:
                for project in PLAYWRIGHT_PROJECT_NAMES:
                    key = f"{slug}-{project}"
                    self._seed_one(
                        f"{local}+{key}@{domain}", password, f"Playwright {key}"
                    )
        else:
            self._seed_one(options["email"], password, options["player_name"])

    @transaction.atomic
    def _seed_one(self, email, password, player_name):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "is_active": True,
                "is_confirmed": True,
                "timezone": "UTC",
            },
        )

        user_updates = []
        if created or not user.check_password(password):
            user.set_password(password)
            user_updates.append("password")
        if not user.is_active:
            user.is_active = True
            user_updates.append("is_active")
        if not user.is_confirmed:
            user.is_confirmed = True
            user_updates.append("is_confirmed")
        if str(user.timezone) != "UTC":
            user.timezone = "UTC"
            user_updates.append("timezone")

        if user_updates:
            user.save(update_fields=user_updates)

        player = ensure_player_setup_for_user(user)
        player_updates = []
        if player.name != player_name:
            player.name = player_name
            player_updates.append("name")
        if player.onboarding_step != 2:
            player.onboarding_step = 2
            player_updates.append("onboarding_step")
        if not player.onboarding_completed:
            player.onboarding_completed = True
            player_updates.append("onboarding_completed")
        if player.is_deleted:
            player.is_deleted = False
            player_updates.append("is_deleted")
        if player.deleted_at is not None:
            player.deleted_at = None
            player_updates.append("deleted_at")
        if player.bio:
            player.bio = ""
            player_updates.append("bio")
        if player.is_online:
            player.is_online = False
            player_updates.append("is_online")
        if player.active_connections != 0:
            player.active_connections = 0
            player_updates.append("active_connections")
        if player.last_seen is not None:
            player.last_seen = None
            player_updates.append("last_seen")
        if player.xp != 0:
            player.xp = 0
            player_updates.append("xp")
        if player.level != 0:
            player.level = 0
            player_updates.append("level")
        if player.xp_next_level != 100:
            player.xp_next_level = 100
            player_updates.append("xp_next_level")
        if player.xp_modifier != 1:
            player.xp_modifier = 1
            player_updates.append("xp_modifier")

        if player_updates:
            player.save(update_fields=player_updates)

        player.activities.all().delete()
        player.tasks.all().delete()
        player.projects.all().delete()

        activity_timer = player.activity_timer
        activity_timer.reset()

        tutorial_step_ids = list(TutorialStep.objects.values_list("id", flat=True))
        if tutorial_step_ids:
            player.tutorial_steps_seen.set(tutorial_step_ids)

        self.stdout.write(
            self.style.SUCCESS(
                f"Playwright user ready: {user.email} (player={player.name})"
            )
        )
