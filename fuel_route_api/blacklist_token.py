from ninja_jwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from ninja_jwt.tokens import RefreshToken

from .helper_db import run_db


async def blacklist_refresh_token(refresh_token: str) -> bool:
    try:
        token = RefreshToken(refresh_token)

       
        await run_db(token.blacklist)

        
        await run_db(lambda: OutstandingToken.objects.filter(jti=token["jti"]).delete())
        await run_db(lambda: BlacklistedToken.objects.filter(token__jti=token["jti"]).delete())

        return True
    except Exception:
        return False
