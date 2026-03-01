from django.core.cache import caches
from ninja_extra.throttling import AnonRateThrottle, UserRateThrottle


class CustomAnonRateThrottle(AnonRateThrottle):
    scope = "anon"
    cache = caches["default"]
    rate = "3/min"


class CustomUserThrottle(UserRateThrottle):
    scope = "user"
    cache = caches["default"]
    rate = "4/min"
