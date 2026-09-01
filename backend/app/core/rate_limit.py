from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.core.config import settings
import os

if os.getenv("TESTING") == "true":
    limiter = Limiter(key_func=get_remote_address, default_limits=["1000/minute"])
else:
    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit_default])


async def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    retry_after = getattr(exc.limit, 'retry_after', None) if exc.limit else None
    response = JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again later.", "retry_after": retry_after},
    )
    response = request.app.state.limiter._inject_headers(response, request.state.view_rate_limit)
    return response


if os.getenv("TESTING") == "true":
    RATE_LIMIT_GENERATION = "1000/hour"
    RATE_LIMIT_LOGIN = "1000/minute"
    RATE_LIMIT_REGISTER = "1000/hour"
    RATE_LIMIT_UPLOAD = "1000/minute"
else:
    RATE_LIMIT_GENERATION = os.getenv("RATE_LIMIT_GENERATION", "10/hour")
    RATE_LIMIT_LOGIN = os.getenv("RATE_LIMIT_LOGIN", "5/minute")
    RATE_LIMIT_REGISTER = os.getenv("RATE_LIMIT_REGISTER", "3/hour")
    RATE_LIMIT_UPLOAD = os.getenv("RATE_LIMIT_UPLOAD", "20/minute")
