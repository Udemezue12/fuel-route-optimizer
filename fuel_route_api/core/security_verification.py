
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from ninja.errors import HttpError
from redis.asyncio import Redis

from fuel_project.celery import app as task_app
from fuel_route_api.breaker.circuit_breaker import breaker
from fuel_route_api.core.env import (
    CELERY_REDIS_URL,
    RESET_PASSWORD_SALT,
    RESET_SECRET_KEY,
    VERIFY_EMAIL_SALT,
    VERIFY_EMAIL_SECRET_KEY,
)
from fuel_route_api.models.get_model import User

from .cache_dependencies import AsyncCacheDependencies
from .repo_dependencies import CRUDDependencies, ExistingDependencies
from .security_generate import user_generate

reset_serializer = URLSafeTimedSerializer(RESET_SECRET_KEY or "")
verify_serializer = URLSafeTimedSerializer(VERIFY_EMAIL_SECRET_KEY or "")
resend_tracker: dict[str, dict] = {}
redis = Redis.from_url(CELERY_REDIS_URL, decode_responses=True)


class UserVerification:
    def __init__(self):
        self.repo = CRUDDependencies()
        self.check = ExistingDependencies()
        self.cache = AsyncCacheDependencies()

    async def verify_reset_token(
        self, token: str, expiration: int = 3600
    ) -> str | None:
        try:
            email = reset_serializer.loads(
                token, salt=RESET_PASSWORD_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None

    async def verify_verify_token(
        self, token: str, expiration: int = 3600
    ) -> str | None:
        try:
            email = verify_serializer.loads(
                token, salt=VERIFY_EMAIL_SALT, max_age=expiration
            )
            return email
        except (SignatureExpired, BadSignature):
            return None

    async def verify_otp(self, otp: str) -> str:
        async def handler():
            async for key in redis.scan_iter(match="otp:*"):
                stored = await redis.get(key)
                if stored == otp:
                    await redis.delete(key)
                    return key.split(":")[1]
            return None

        return await breaker.call(handler)

    async def resend_verification_link(
        self, email: str
    ):
        user = await self.repo.async_get_object_or_404(model=User, email=email)
        if not user:
            raise HttpError(status_code=404, message="User not found")
        if user.is_verified:
            raise HttpError(status_code=400, message="Email already verified.")

        otp = await user_generate.generate_otp(email)
        token = await user_generate.generate_verify_token(email)
        name = f"{user.last_name} {user.first_name}"
        task_app.send_task(
            "send_verify_email_notification",
            args=[str(user.phone_number), str(user.email),
                  str(otp), str(name), str(token)]

        )
        return {"message": "Verification Link via your email resent."}

    async def resend_password_reset_link(
        self, email: str,
    ):
        user = await self.repo.async_get_object_or_404(model=User, email=email)
        if not user:
            raise HttpError(status_code=404, message="User not found")

        otp = await user_generate.generate_otp(email)
        token = await user_generate.generate_reset_token(email)
        name = f"{user.last_name} {user.first_name}"

        task_app.send_task(
            "send_password_reset_notification",
            args=[str(user.phone_number), str(user.email),
                  str(otp), str(name), str(token)]

        )
        return {"message": "Password reset link via your email resent successfully."}

    async def verify_email(self, otp: str | None = None, token: str | None = None):
        if otp and otp.strip():
            email = await self.verify_otp(otp)
        elif token:
            email = await self.verify_verify_token(token)
        else:
            raise HttpError(status_code=400,
                            message="No verification data provided")
        if not email:
            raise HttpError(
                status_code=400,
                message="Invalid or expired verification token",
            )
        user = await self.repo.async_get_object_or_404(model=User, email=email)
        user.is_verified = True
        user_id = user.id
        await self.repo.asave(user)
        await self.cache.delete_from_cache(f"users::{user_id}")
        return {"message": "Email verified successfully"}
