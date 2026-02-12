from datetime import timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def handle_first_login_of_day(user):
    """
    Called the first time a user logs in on a given day.
    Put streak updates, notifications, analytics, etc. here.
    """
    # Example: log info
    print(f"[LOGIN SERVICE] First login today for {user.email}")

    # Here you could:
    # - Update streaks (optional, since properties are dynamic)
    # - Send ServerMessages
    # - Trigger achievements, rewards, etc.

    player = getattr(user, "player", None)
    if not player:
        return

    today = timezone.localdate()

    # Get the most recent login BEFORE today
    previous_login = (
        user.logins.filter(timestamp__date__lt=today).order_by("-timestamp").first()
    )

    streak = user.current_login_streak

    if streak == 1 and previous_login:
        message_text = "Welcome back, we missed you! Your login streak has been reset."
    else:
        message_text = f"Welcome back! Your login streak is now {streak} days."
    # Send server message
    from gameplay.models import ServerMessage

    ServerMessage.objects.create(
        group=player.group_name,
        type="notification",
        action="notification",
        data={},
        message=message_text,
        is_draft=False,
    )


def current_login_streak(cls, login_dates):
    """Current consecutive-day login streak, including today."""
    streak = 0
    today = timezone.localdate()
    login_dates_set = set(login_dates)
    day = today
    while day in login_dates_set:
        streak += 1
        day -= timedelta(days=1)
    return streak


def max_login_streak(cls, login_dates):
    """Maximum consecutive-day login streak ever."""
    max_streak = 1
    current_streak = 1
    for i in range(1, len(login_dates)):
        if login_dates[i] == login_dates[i - 1] + timedelta(days=1):
            current_streak += 1
        else:
            current_streak = 1
        max_streak = max(max_streak, current_streak)
    return max_streak


def update_login_streak(user):
    """
    Update Player login streak based on UserLogin entries.
    This should be called after a successful JWT login.
    """
    player = user.player
    today = timezone.localdate()
    message_text = ""
    if user.last_login:
        last_login_date = user.last_login.local_date()
        if last_login_date == today:
            message_text = "Welcome back! You logged in earlier today."
        elif last_login_date == today - timedelta(days=1):
            message_text = f"Welcome back! You logged in yesterday. Your login streak is now {user.current_login_streak} days."
        else:
            message_text = (
                "Welcome back, we missed you! Your login streak has been reset."
            )
    else:
        # First-ever login
        message_text = "Welcome! This is your first login, starting your streak."

    # Send server message
    from gameplay.models import ServerMessage

    ServerMessage.objects.create(
        group=player.group_name,
        type="notification",
        action="notification",
        data={},
        message=message_text,
        is_draft=False,
    )

    logger.info(
        f"[UPDATE LOGIN STREAK] {user.email}: streak={user.current_login_streak}, max={user.max_login_streak}, total={user.days_logged_in}"
    )
