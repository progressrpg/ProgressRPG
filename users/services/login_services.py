from datetime import timedelta

from django.utils import timezone

from users.models import UserLogin


def _build_login_message(previous_login, today, streak):
    if not previous_login:
        return "Welcome! This is your first login, starting your streak."

    previous_login_day = timezone.localtime(previous_login.timestamp).date()
    if previous_login_day == today:
        return "Welcome back! You logged in earlier today."
    if previous_login_day == today - timedelta(days=1):
        return f"Welcome back! Your login streak is now {streak} days."
    return "Welcome back, we missed you! Your login streak has been reset."


def update_login_streak(user):
    """Return a user-facing login message derived from UserLogin history."""
    player = getattr(user, "player", None)
    if not player:
        return ""

    latest_login = user.logins.order_by("-timestamp").first()
    if not latest_login:
        return ""

    if not latest_login.is_first_login_of_day():
        return "Welcome back! You logged in earlier today."

    previous_login = (
        user.logins.filter(timestamp__lt=latest_login.timestamp)
        .order_by("-timestamp")
        .first()
    )
    return _build_login_message(
        previous_login,
        latest_login.local_date(),
        UserLogin.current_login_streak(user),
    )


def handle_first_login_of_day(user):
    """Compatibility wrapper around the login streak updater."""
    return update_login_streak(user)
