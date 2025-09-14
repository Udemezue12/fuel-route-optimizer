from typing import Any, List, cast

from asgiref.sync import sync_to_async
from django.contrib.auth import (
    authenticate,
    login as django_login,
    logout as django_logout,
)
from django.contrib.auth.models import User
from django.http import HttpRequest as Request
from django.utils.timezone import now
from injector import inject
from ninja.errors import HttpError
from ninja.responses import Response as JSONResponse
from ninja_extra import api_controller, http_get, http_post, throttle
from ninja_extra.permissions import IsAdminUser
from ninja_jwt.tokens import RefreshToken

from .blacklist_token import blacklist_refresh_token
from .dependencies import CacheDependencies, CRUDDependencies, ExistingDependencies
from .helper import run_sync
from .schema import LoginSchema, UserIn, UserOut
from .throttling import CustomAnonRateThrottle, CustomUserThrottle
from .tokens import TokenRequest


@api_controller("/users", tags=["USERS"])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class AuthController:
    @inject
    def __init__(
        self,
        deps: CRUDDependencies,
        cache: CacheDependencies,
        check_existing: ExistingDependencies,
        csrf_validate: TokenRequest,
    ):
        self.deps = deps
        self.check_existing = check_existing
        self.csrf_validate = csrf_validate
        self.cache = cache

    @http_get("", response=List[UserOut], permissions=[IsAdminUser])
    async def users(self):
        deps = self.deps

        users = await deps.get_lists(model=User)
        return users

    @http_post("/register", response=UserOut)
    async def register(self, request: Request, data: UserIn):
        await self.csrf_validate.validate_csrf(request)
        deps = self.deps
        check_existing = self.check_existing
        username = data.username
        first_name = data.first_name
        password = data.password
        last_name = data.last_name
        email = data.email
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
        )
        user.set_password(password)
        await user.asave()
        return UserOut(
            email=user.email,
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=last_name,
        )

    @http_post("/login")
    async def login(self, request: Request, data: LoginSchema):
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

        response = JSONResponse(
            {
                "username": user.username,
                "email": user.email,
                "user_id": user.id,
                "access_token": access_token,
                # "refresh_token": refresh,
                "message": "Login successful",
            }
        )
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=600,
        )
        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=False,
            samesite="Lax",
            max_age=86400,
        )

        return response

    @http_post("/refresh")
    async def refresh_token(self, request: Request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            raise HttpError(status_code=401, message="Refresh token not provided")

        try:
            refresh = RefreshToken(refresh_token)
            user_id = refresh["user_id"]
            last_seen = self.cache.get_from_cache(f"user:{user_id}:last_seen")
            if last_seen and (now().timestamp() - last_seen > 1800):  

                raise HttpError(status_code=401, message="Session expired due to inactivity")
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

    @http_post("/logout")
    async def logout(self, request: Request):
        await run_sync(django_logout, request)
        refresh_token = request.COOKIES.get("refresh_token")
       
        if refresh_token:
            try:
               await blacklist_refresh_token(refresh_token)
            except Exception:
                pass
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
