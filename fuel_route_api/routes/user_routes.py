from typing import List

from django.http import HttpRequest as Request
from injector import inject
from ninja_extra import api_controller, http_get, http_post, throttle
from ninja_extra.permissions import IsAdminUser

from fuel_route_api.core.security_verification import UserVerification
from fuel_route_api.core.throttling import CustomAnonRateThrottle, CustomUserThrottle
from fuel_route_api.schema.schema import (
    ForgotPasswordSchema,
    LoginSchema,
    ResetPasswordSchema,
    UserIn,
    UserOut,
    VerifyEmail,
)
from fuel_route_api.services.user_service import UserService


@api_controller("/v2/users", tags=["User Authenication"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class AuthController:
    @inject
    def __init__(self):
        self.user_service = UserService()
        self.user_verify = UserVerification()

    @http_get("", response=List[UserOut], permissions=[IsAdminUser])
    async def users(self):
        return await self.user_service.users()

    @http_post("/register")
    async def register(self, request: Request, data: UserIn):
        return await self.user_service.register(request=request, data=data)

    @http_post("/login")
    async def login(self, request: Request, data: LoginSchema):
        return await self.user_service.login(request=request, data=data)

    @http_post("/refresh")
    async def refresh_token(self, request: Request):
        return await self.user_service.refresh_token(request)

    @http_post("/logout")
    async def logout(self, request: Request):
        return await self.user_service.logout(request)

    @http_post("/verify-email")
    async def verify_email(self, data: VerifyEmail):
        return await self.user_verify.verify_email(otp=data.otp, token=data.otp)

    @http_post("/forgot-password")
    async def forgot_password(self, data: ForgotPasswordSchema):
        return await self.user_service.forgot_password(payload=data)

    @http_post("/reset-password")
    async def reset_password(self, data: ResetPasswordSchema):
        return await self.user_service.reset_password(payload=data)

    @http_post("/resend-email-verification")
    async def resend_verify_email_link(self, email: str):
        return await self.user_verify.resend_verification_link(email=email)

    @http_post("/resend-password-reset-link")
    async def resend_password_reset_link(self, email: str):
        return await self.user_verify.resend_password_reset_link(email=email)
