"""Security headers and rate limiting middlewares for production hardening."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Enforce OWASP recommended security headers on every response."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Sliding-window in-memory rate limiter per client IP.

    Defaults to 60 requests per 60-second window.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        window_seconds: int = 60,
        exempt_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.exempt_paths = exempt_paths or []
        self._history: dict[str, list[float]] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        # Check X-Forwarded-For if behind reverse proxy
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "127.0.0.1"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Response]) -> Response:
        # Check exemption
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        now = time.time()
        client_key = self._get_client_key(request)
        window_start = now - self.window_seconds

        # Clean older timestamps
        recent_timestamps = [ts for ts in self._history[client_key] if ts > window_start]
        self._history[client_key] = recent_timestamps

        if len(recent_timestamps) >= self.requests_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please retry after some time."},
                headers={"Retry-After": str(self.window_seconds)},
            )

        self._history[client_key].append(now)
        return await call_next(request)
