from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest as Request
from django.utils.deprecation import MiddlewareMixin
from django.utils.timezone import now
from jwt import decode
from jwt.exceptions import DecodeError, ExpiredSignatureError

from .env import ALGORITHM, SECRET_KEY
from .dependencies import CacheDependencies


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request: Request):
        token = request.COOKIES.get("access_token")
        if token:
            try:
                payload = decode(token, SECRET_KEY, ALGORITHM)
                user = get_user_model().objects.get(id=payload["user_id"])
                request.user = user
            except (ExpiredSignatureError, DecodeError, get_user_model().DoesNotExist):
                request.user = AnonymousUser()


class AutoLogoutMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            last_activity = request.session.get("last_activity")
            current_time = now().timestamp()

            if last_activity and (current_time - last_activity > 600):  # 5 mins
                from django.contrib.auth import logout

                logout(request)
                request.session.flush()
            else:
                request.session["last_activity"] = current_time

        return self.get_response(request)

# class ActivityMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         cache = CacheDependencies()
#         if request.user.is_authenticated:
#             from django.utils.timezone import now
#             cache.set_from_cache(f"user:{request.user.id}:last_seen", now().timestamp(), timeout=86400)
#         return self.get_response(request)
