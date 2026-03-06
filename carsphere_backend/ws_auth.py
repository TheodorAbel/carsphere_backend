from urllib.parse import parse_qs
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _get_user(user_id):
    User = get_user_model()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return AnonymousUser()


class JwtAuthMiddleware:
    """
    Token auth for Django Channels via query param:
    ws://host/ws/notifications/?token=JWT
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = params.get('token', [None])[0]

        scope['user'] = AnonymousUser()
        if token:
            try:
                access = AccessToken(token)
                user_id = access.get('user_id')
                if user_id is not None:
                    scope['user'] = await _get_user(user_id)
            except Exception:
                scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)
