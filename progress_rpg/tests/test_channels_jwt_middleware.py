from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TransactionTestCase
from rest_framework_simplejwt.tokens import AccessToken

from progress_rpg.middleware.channels_jwt import QueryStringJWTAuthMiddleware


class QueryStringJWTAuthMiddlewareTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="websocket-auth@example.com",
            password="test-pass-123",
        )

    def _run_middleware(self, query_string):
        captured = {}

        async def inner(scope, receive, send):
            captured["user"] = scope["user"]

        middleware = QueryStringJWTAuthMiddleware(inner)
        scope = {
            "type": "websocket",
            "headers": [],
            "query_string": query_string,
        }

        async def receive():
            return {"type": "websocket.disconnect"}

        async def send(message):
            return message

        async_to_sync(middleware)(scope, receive, send)
        return captured["user"]

    def test_sets_authenticated_user_from_valid_token_query_param(self):
        token = str(AccessToken.for_user(self.user))

        user = self._run_middleware(f"token={token}".encode("utf-8"))

        self.assertEqual(user.pk, self.user.pk)
        self.assertTrue(user.is_authenticated)

    def test_leaves_anonymous_user_when_token_is_missing(self):
        user = self._run_middleware(b"")

        self.assertIsInstance(user, AnonymousUser)
        self.assertFalse(user.is_authenticated)

    def test_leaves_anonymous_user_when_token_is_invalid(self):
        user = self._run_middleware(b"token=not-a-real-token")

        self.assertIsInstance(user, AnonymousUser)
        self.assertFalse(user.is_authenticated)
