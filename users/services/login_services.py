from datetime import timedelta

from django.utils import timezone

from users.models import UserLogin


LOGIN_STATE_NONE = "none"
LOGIN_STATE_FIRST_LOGIN_EVER = "first_login_ever"
LOGIN_STATE_ALREADY_LOGGED_TODAY = "already_logged_today"
LOGIN_STATE_STREAK_CONTINUES = "streak_continues"
LOGIN_STATE_STREAK_RESET = "streak_reset"


def _build_login_message(previous_login, today, streak):
    if not previous_login:
        return "Welcome! This is your first login, starting your streak."

    previous_login_day = timezone.localtime(previous_login.timestamp).date()
    if previous_login_day == today:
        return "Welcome back! You logged in earlier today."
    if previous_login_day == today - timedelta(days=1):
        return f"Welcome back! Your login streak is now {streak} days."
    return "Welcome back, we missed you! Your login streak has been reset."


def get_login_state(user):
    """Return normalized login state used by API consumers."""
    player = getattr(user, "player", None)
    if not player:
        return {
            "login_state": LOGIN_STATE_NONE,
            "login_streak": 0,
            "login_event_at": None,
        }

    latest_login = user.logins.order_by("-timestamp").first()
    if not latest_login:
        return {
            "login_state": LOGIN_STATE_NONE,
            "login_streak": 0,
            "login_event_at": None,
        }

    login_event_at = latest_login.timestamp.isoformat()

    streak = UserLogin.current_login_streak(user)
    if not latest_login.is_first_login_of_day():
        return {
            "login_state": LOGIN_STATE_ALREADY_LOGGED_TODAY,
            "login_streak": streak,
            "login_event_at": login_event_at,
        }

    previous_login = (
        user.logins.filter(timestamp__lt=latest_login.timestamp)
        .order_by("-timestamp")
        .first()
    )

    if not previous_login:
        state = LOGIN_STATE_FIRST_LOGIN_EVER
    else:
        previous_login_day = timezone.localtime(previous_login.timestamp).date()
        latest_login_day = latest_login.local_date()
        if previous_login_day == latest_login_day - timedelta(days=1):
            state = LOGIN_STATE_STREAK_CONTINUES
        else:
            state = LOGIN_STATE_STREAK_RESET

    return {
        "login_state": state,
        "login_streak": streak,
        "login_event_at": login_event_at,
    }


def update_login_streak(user):
    """Return a user-facing login message derived from UserLogin history."""
    login_state = get_login_state(user)
    streak = login_state["login_streak"]

    if login_state["login_state"] == LOGIN_STATE_FIRST_LOGIN_EVER:
        return "Welcome! This is your first login, starting your streak."
    if login_state["login_state"] == LOGIN_STATE_ALREADY_LOGGED_TODAY:
        return "Welcome back! You logged in earlier today."
    if login_state["login_state"] == LOGIN_STATE_STREAK_CONTINUES:
        return f"Welcome back! Your login streak is now {streak} days."
    if login_state["login_state"] == LOGIN_STATE_STREAK_RESET:
        return "Welcome back, we missed you! Your login streak has been reset."
    return ""


def handle_first_login_of_day(user):
    """Compatibility wrapper around the login streak updater."""
    return update_login_streak(user)
