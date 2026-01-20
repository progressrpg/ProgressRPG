# users/auth_backends.py

from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger("errors")

User = get_user_model()


class EmailBackend:
    def authenticate(self, request, username=None, password=None, **kwargs):
        email = username or kwargs.get("email")
        if not email or not password:
            logger.debug("Email or password not provided, returning None")
            return None

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            logger.debug(f"No user found with email: {email}")
            return None

        if user.check_password(password):
            if user.is_active:
                logger.debug(f"Authentication successful for user: {user}")
                return user
            else:
                logger.debug(f"User is inactive: {user}")
                return None
        else:
            logger.debug(f"Incorrect password for user: {user}")
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
