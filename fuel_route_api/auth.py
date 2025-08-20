from typing import List, cast, Any
from asgiref.sync import sync_to_async
from injector import inject
from ninja.errors import HttpError
from ninja.responses import Response as JSONResponse
from ninja_jwt.tokens import RefreshToken
from ninja_extra import api_controller, http_get, http_post, throttle
from ninja_extra.permissions import IsAdminUser
from django.http import HttpRequest as Request
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as django_login
from .dependencies import CRUDDependencies, ExistingDependencies
from .throttling import CustomAnonRateThrottle, CustomUserThrottle
from .schema import UserIn, UserOut, LoginSchema
from .tokens import TokenRequest


@api_controller('/users', tags=['USERS'])
@throttle(CustomAnonRateThrottle, CustomUserThrottle)
class AuthController:
    @inject
    def __init__(self, deps: CRUDDependencies, check_existing: ExistingDependencies, csrf_validate: TokenRequest):
        self.deps = deps
        self.check_existing = check_existing
        self.csrf_validate = csrf_validate

    @http_get('', response=List[UserOut], permissions=[IsAdminUser])
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
        await check_existing.async_check_existing(model=User, raise_error_if_exists=True, email=email, error_field='Email')
        await check_existing.async_check_existing(model=User, raise_error_if_exists=True, username=username, error_field='Username')
        await check_existing.async_check_existing(model=User, raise_error_if_exists=True, first_name=first_name, error_field='First_Name')
        await check_existing.async_check_existing(model=User, raise_error_if_exists=True, last_name=last_name, error_field='Last_Name')
        user = await deps.async_create(model=User, username=username, first_name=first_name, last_name=last_name, email=email)
        user.set_password(password)
        await user.asave()
        return UserOut(
            email=user.email,
            id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=last_name

        )

    @http_post('/login')
    async def login(self, request: Request,  data: LoginSchema):
        await self.csrf_validate.validate_csrf(request)
        username = data.username
        password = data.password

        user = await sync_to_async(authenticate)(request, username=username, password=password)
        if not user:
            raise HttpError(status_code=401, message='Invalid credentials')
        await sync_to_async(django_login)(request, user)
        refresh = RefreshToken.for_user(user)

        access_token = str(cast(Any, refresh).access_token)

        response = JSONResponse({
            "username": user.username,
            "email": user.email,
            "user_id": user.id,
            'access_token': access_token,
            "message": "Login successful"
        })
        response.set_cookie(key="access_token",
                            value=access_token,
                            httponly=True, secure=False, samesite="Lax", max_age=86400)

        return response

    @http_post('/logout')
    async def logout(self, request: Request,):
        request.session.clear()
        res = JSONResponse({"message": "Logged out"})

        for cookie in ["sessionid", "session", "csrf_token", "access_token"]:
            res.delete_cookie(key=cookie, path="/")

        return res
