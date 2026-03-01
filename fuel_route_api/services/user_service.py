from typing import Any, cast

from asgiref.sync import sync_to_async
from django.contrib.auth import authenticate
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.http import HttpRequest as Request
from django.utils.timezone import now
from injector import inject
from ninja.errors import HttpError
from ninja.responses import Response as JSONResponse
from ninja_jwt.tokens import RefreshToken

from fuel_project.celery import app as task_app
from fuel_route_api.core.blacklist_token import blacklist_refresh_token
from fuel_route_api.core.cache_dependencies import AsyncCacheDependencies
from fuel_route_api.core.helper import run_sync
from fuel_route_api.core.repo_dependencies import (CRUDDependencies,
                                                   ExistingDependencies)
from fuel_route_api.core.security_generate import UserGenerate
from fuel_route_api.core.security_verification import UserVerification
from fuel_route_api.models.get_model import User


from ..tokens import TokenRequest


class UserService:
    @inject
    def __init__(
        self,

    ):
        self.deps = CRUDDependencies()
        self.check_existing = ExistingDependencies()
        self.csrf_validate = TokenRequest()
        self.cache = AsyncCacheDependencies()
        self.generate = UserGenerate()
        self.verification = UserVerification()

    async def users(self):
        deps = self.deps

        users = await deps.get_lists(model=User)
        return users

    async def register(self, request: Request, data):
        await self.csrf_validate.validate_csrf(request)
        deps = self.deps
        check_existing = self.check_existing
        username = data.username
        first_name = data.first_name
        password = data.password
        last_name = data.last_name
        email = data.email
        phone_number=data.phone_number
        await check_existing.async_check_existing(
            model=User, raise_error_if_exists=True, email=email, error_field="Email"
        )
        await check_existing.async_check_existing(
            model=User,
            raise_error_if_exists=True,
            username=username,
            error_field="Username",
        )
        await check_existing.async_check_existing(
            model=User,
            raise_error_if_exists=True,
            first_name=first_name,
            error_field="First_Name",
        )
        await check_existing.async_check_existing(
            model=User,
            raise_error_if_exists=True,
            last_name=last_name,
            error_field="Last_Name",
        )
        user = await deps.async_create(
            model=User,
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            is_verified=False,
            phone_number=phone_number
        )
        user.set_password(password)
        await user.asave()
        if user:
            token = await self.generate.generate_reset_token(user.email)
            otp = await self.generate.generate_otp(user.email)
            name = f"{user.last_name} {user.first_name}"
            task_app.send_task(
                "send_verify_email_notification",
                args=[str(user.phone_number), str(user.email),
                      str(otp), str(name), str(token)]

            )
        return {
            "message": "Your registration was successful. Kindly check your email inbox or SMS to complete account verification."
        }

    async def login(self, request: Request, data):
        await self.csrf_validate.validate_csrf(request)
        username = data.username
        password = data.password

        user = await run_sync(
            authenticate, request, username=username, password=password
        )

        if not user:
            raise HttpError(status_code=401, message="Invalid credentials")
        await run_sync(django_login, request, user)
        refresh = await sync_to_async(RefreshToken.for_user)(user)

        access_token = str(cast(Any, refresh).access_token)
        refresh_token = str(refresh)

        response = JSONResponse(
            {
                "message": "Login successful",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
            }
        )

        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=60 * 10,
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=86400,
        )

        return response

    async def refresh_token(self, request: Request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            raise HttpError(status_code=401,
                            message="Refresh token not provided")

        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh["user_id"]
            last_seen = self.cache.get_from_cache(f"user:{user_id}:last_seen")
            if last_seen and (now().timestamp() - last_seen > 1800):

                raise HttpError(status_code=401,
                                message="Session expired due to inactivity")
            new_access_token = await sync_to_async(lambda: str(refresh.access_token))()
            response = JSONResponse(
                {
                    "access_token": new_access_token,
                    "message": "Token refreshed successfully",
                }
            )
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=300,
            )
            return response
        except Exception:
            raise HttpError(status_code=401, message="Invalid refresh token")

    async def logout(self, request: Request):
        await run_sync(django_logout, request)
        refresh_token = request.COOKIES.get("refresh_token")
        access_token = request.COOKIES.get("access_token")

        if refresh_token:

            await blacklist_refresh_token(refresh_token)
        if access_token:
            await blacklist_refresh_token(access_token)

        res = JSONResponse({"detail": "Logout successful"}, status=200)

        for cookie in [
            "sessionid",
            "session",
            "csrf_token",
            "csrftoken",
            "access_token",
            "refresh_token",
        ]:
            res.delete_cookie(key=cookie, path="/")

        return res

    async def forgot_password(self, payload):
        user = await self.deps.async_get_object_or_404(User, email=payload.email)
        if user:
            token = await self.generate.generate_reset_token(user.email)
            otp = await self.generate.generate_otp(user.email)
            name = f"{user.last_name} {user.first_name}"
            task_app.send_task(
                "send_password_reset_notification",
                args=[str(user.phone_number), str(user.email),
                      str(otp), str(name), str(token)]

            )
        return {
            "message": "If the email and phoneNumber exists, a reset link has been sent."
        }

    async def reset_password(self, payload):
        email = None

        if payload.token:
            try:
                email = await self.verification.verify_reset_token(
                    payload.token
                )
            except Exception:
                pass

        if not email and payload.otp:
            try:
                email = await self.verification.verify_otp(payload.otp)
            except Exception:
                pass

        if not email:
            raise HttpError(
                status_code=400,
                message="Invalid or expired token",
            )
        user = await self.deps.async_get_object_or_404(User,  email=email)
        if not user:
            raise HttpError(status_code=404, message="User not found")
        user.set_password(payload.new_password)
        await self.deps.asave(user)
        return {"message": "Password reset successfully"}
