from ninja_extra.throttling import AnonRateThrottle, UserRateThrottle
from django.core.cache import caches


class CustomAnonRateThrottle(AnonRateThrottle):
    scope = 'anon'
    cache = caches['default']
    rate = '50/hour'


class CustomUserThrottle(UserRateThrottle):
    scope = 'user'
    cache = caches['default']
    rate = '200/hour'
