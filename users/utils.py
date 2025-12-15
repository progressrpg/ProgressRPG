"""
Utility Functions for User Management

This module provides utility functions to support user-related operations, such as
assigning characters to profiles and sending user notifications. These utilities
are designed to streamline key processes in the application, enhancing user experience
and ensuring consistency in functionality.

Usage:
These functions are essential for managing user interactions and onboarding, ensuring that
new users are properly initialized with characters and receive email notifications during
the account creation process.

Author:
    Duncan Appleby

"""

from django.conf import settings
from django.contrib.sessions.models import Session
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

# from django.utils.html import strip_tags
from django.utils import timezone
import logging, sys

from .tasks import send_email_to_users_task
from character.models import Character, PlayerCharacterLink
from gameplay.models import QuestTimer, Quest

logger = logging.getLogger("django")


def assign_character_to_profile(profile):
    """
    Assign a default Character (non-player character) to the given Profile. Deactivates
    any currently active character and associates a new NPC with the Profile. If the
    Profile is recent, assigns a tutorial quest to the newly linked character.

    :param profile: The Profile to which a character will be assigned.
    :type profile: Profile
    :raises ValueError: If the tutorial quest is not found in the database.
    """

    character = Character.objects.filter(
        is_npc=True, can_link=True, death_date__isnull=True
    ).first()

    if not character:
        logger.warning(f"No available NPC character to assign to profile {profile.id}")
        return None

    PlayerCharacterLink.assign_character(profile=profile, character=character)

    qt, created = QuestTimer.objects.get_or_create(character=character)

    if not ("test" in sys.argv):
        tut_quest = Quest.objects.filter(name="[TUTORIAL] Getting started").first()
        if not tut_quest:
            logger.warning(f"Tutorial quest '[TUTORIAL] Getting started' not found!")
        elif created or profile.created_at > (
            timezone.now() - timezone.timedelta(days=14)
        ):
            qt.change_quest(tut_quest, 60)

    return character


def send_email_to_users(users, subject, template_base, context=None, cc_admin=False):
    """
    Schedules email sending as a Celery task.
    """

    # Normalise recipients like your original code
    emails = [user.email if hasattr(user, "email") else user for user in users]

    logger.info(f"[QUEUE EMAIL] Queuing '{subject}' to: {emails}")

    send_email_to_users_task.delay(
        emails=emails,
        subject=subject,
        template_base=template_base,
        context=context or {},
        cc_admin=cc_admin,
    )


def send_email_to_users_sync(
    users, subject, template_base, context=None, cc_admin=False
):
    """
    Sends email to users synchronously.
    """
    if context is None:
        context = {}

    from_email = settings.DEFAULT_FROM_EMAIL
    admin_email = "admin@progressrpg.com"

    # Prepare templates
    plain_message = render_to_string(f"{template_base}.txt", context)
    html_message = render_to_string(f"{template_base}.html", context)

    # Normalise recipients
    emails = [user.email if hasattr(user, "email") else user for user in users]
    if cc_admin:
        emails.append(admin_email)

    logger.info(f"[SEND EMAIL] Sending '{subject}' to: {emails}")

    email = EmailMultiAlternatives(
        subject,
        plain_message,
        from_email,
        emails,
    )
    email.attach_alternative(html_message, "text/html")

    email.send()


def send_signup_email(user):
    """
    Sends a welcome email to a newly registered user.
    """
    context = {"email": user.email, "current_year": timezone.now().year}
    send_email_to_users(
        users=[user],
        subject="Welcome to Progress!",
        template_base="emails/welcome_email",
        context=context,
        cc_admin=True,
    )


def kick_old_sessions(user, current_session_key=None):
    """
    Deletes all active sessions for a user except the current one.
    """
    logger.info(
        f"[KICK OLD SESSIONS] User {user.id} logged in. Checking for old sessions."
    )

    try:

        try:
            sessions = Session.objects.filter(expire_date__gte=timezone.now())
            logger.debug(f"[KICK OLD SESSIONS] Filtered sessions: {sessions}")
        except Exception as e:
            logger.error(f"[KICK OLD SESSIONS] Error filtering sessions: {e}")
            return

        for session in sessions:
            try:
                data = session.get_decoded()
                # logger.debug(f"[KICK OLD SESSIONS] Session key: {session.session_key}, data: {data}")
                # logger.debug(f"[KICK OLD SESSIONS] Session userid: {data.get('_auth_user_id')}")

                if data.get("_auth_user_id") == str(user.id):
                    if session.session_key != current_session_key:
                        # logger.debug(f"[KICK OLD SESSIONS] Killing other sessions for user {user.id}. Session key: {session.session_key}")
                        session.delete()
            except Exception as e:
                logger.error(
                    f"[KICK OLD SESSIONS] Error processing session {session.session_key}: {e}"
                )

    except Exception as e:
        logger.error(f"[KICK OLD SESSIONS] Unexpected error: {e}")
