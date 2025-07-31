from jwt import decode
from jwt.exceptions import ExpiredSignatureError, DecodeError
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest as Request
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from .env import SECRET_KEY, ALGORITHM



# class JWTAuthenticationMiddleware(MiddlewareMixin):

#     def process_request(self, request: Request):
#         token = request.COOKIES.get('access_token')
#         if token:
#             try:
#                 payload = decode(token, SECRET_KEY, ALGORITHM)
#                 user = get_user_model().objects.get(id=payload['user_id'])
#                 request.user = user
#             except (ExpiredSignatureError, DecodeError, get_user_model().DoesNotExist):
#                 request.user = AnonymousUser()
class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request: Request):
        token = request.COOKIES.get('access_token')
        csrf_token = request.headers.get('X-CSRF-TOKEN') or request.COOKIES.get('csrftoken')
        session_csrf_token = request.session.get('csrf_token')

        if token:
            try:
                payload = decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user = get_user_model().objects.get(id=payload['user_id'])

                
                if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
                    if not csrf_token or csrf_token != session_csrf_token:
                        request.user = AnonymousUser()
                        return

                request.user = user
            except (ExpiredSignatureError, DecodeError, get_user_model().DoesNotExist):
                request.user = AnonymousUser()
        else:
            request.user = AnonymousUser()