import logging
from urllib.parse import parse_qs

from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger("general")

SUPPORTED_TOKEN_QUERY_PARAMS = ("token", "access_token")


@database_sync_to_async
def get_user_from_token(raw_token):
    authenticator = JWTAuthentication()
    validated_token = authenticator.get_validated_token(raw_token)
    return authenticator.get_user(validated_token)


class QueryStringJWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        close_old_connections()

        scope = dict(scope)
        current_user = scope.get("user")

        if current_user is None:
            scope["user"] = AnonymousUser()

        raw_token = self._extract_token(scope)
        if raw_token:
            try:
                scope["user"] = await get_user_from_token(raw_token)
            except (AuthenticationFailed, InvalidToken, TokenError) as exc:
                logger.warning(
                    "WebSocket JWT authentication failed.",
                    exc_info=exc,
                )
                if scope.get("user") is None:
                    scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @staticmethod
    def _extract_token(scope):
        query_string = scope.get("query_string", b"")
        params = parse_qs(query_string.decode("utf-8"))

        for key in SUPPORTED_TOKEN_QUERY_PARAMS:
            values = params.get(key)
            if values:
                return values[0]

        return None


def JWTQueryStringAuthMiddlewareStack(inner):
    return AuthMiddlewareStack(QueryStringJWTAuthMiddleware(inner))
