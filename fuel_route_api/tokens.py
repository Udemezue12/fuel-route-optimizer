import logging
from secrets import token_hex

from asgiref.sync import sync_to_async
from django.http import HttpRequest as Request
from ninja.errors import HttpError
from ninja_extra import api_controller, http_get

from .schema import CsrfTokenSchema

logger = logging.getLogger(__name__)


@api_controller("/csrf", tags=["CSRF TOKEN"])
class TokenRequest:
    @http_get("/token", response=CsrfTokenSchema)
    def get_csrf_token(self, request: Request) -> str:
        csrf_token = token_hex(35)
        request.session["csrf_token"] = csrf_token
        return {"csrf_token": csrf_token}

    async def validate_csrf(self, request: Request):
        header_token = await sync_to_async(request.headers.get)("X-CSRF-TOKEN")
        session_token = await sync_to_async(request.session.get)("csrf_token")

        logger.debug(f"Header token: {header_token}")
        logger.debug(f"Session token: {session_token}")

        if not session_token:
            raise HttpError(403, "Missing CSRF token")

        # if header_token != session_token:
        #     raise HttpError(403, "Invalid CSRF token")
