from jwt import decode
from jwt.exceptions import ExpiredSignatureError, DecodeError
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest as Request
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from .env import SECRET_KEY, ALGORITHM



class JWTAuthenticationMiddleware(MiddlewareMixin):

    def process_request(self, request: Request):
        token = request.COOKIES.get('access_token')
        if token:
            try:
                payload = decode(token, SECRET_KEY, ALGORITHM)
                user = get_user_model().objects.get(id=payload['user_id'])
                request.user = user
            except (ExpiredSignatureError, DecodeError, get_user_model().DoesNotExist):
                request.user = AnonymousUser()