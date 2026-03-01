import secrets
from random import randint


from itsdangerous import URLSafeTimedSerializer

from fuel_route_api.breaker.circuit_breaker import breaker
from .env import CELERY_REDIS_URL, RESET_PASSWORD_SALT, RESET_SECRET_KEY, VERIFY_EMAIL_SECRET_KEY, VERIFY_EMAIL_SALT
from redis.asyncio import Redis
reset_serializer = URLSafeTimedSerializer(RESET_SECRET_KEY)
verify_serializer = URLSafeTimedSerializer(VERIFY_EMAIL_SECRET_KEY)

redis = Redis.from_url(CELERY_REDIS_URL, decode_responses=True)


class UserGenerate:

    async def generate_csrf_token(self) -> str:
        return secrets.token_hex(32)

    async def generate_verify_token(self, email: str) -> str:
        return verify_serializer.dumps(email, salt=VERIFY_EMAIL_SALT)

    async def generate_reset_token(self, email: str) -> str:
        return reset_serializer.dumps(email, salt=RESET_PASSWORD_SALT)

    async def generate_otp(self, email: str) -> str:
        async def handler():
            otp = str(randint(100000, 999999))
            await redis.setex(f"otp:{email}", 300, otp)
            return otp

        return await breaker.call(handler)


user_generate = UserGenerate()
