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

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Response]
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none';"
        )
        return response


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Shared limits in production; bounded local fallback for development."""

    def __init__(
        self, app, requests_per_minute=60, window_seconds=60, exempt_paths=None
    ):
        from collections import OrderedDict

        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self.exempt_paths = exempt_paths or ["/health"]
        self._history = OrderedDict()
        self._redis = None

    def _get_client_key(self, request):
        # ASGI server must trust only the configured reverse proxy. Never parse caller headers here.
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request, call_next):
        import hashlib
        import redis.asyncio as redis
        from app.config import settings

        if request.method == "OPTIONS" or request.url.path in self.exempt_paths:
            return await call_next(request)
        key = self._get_client_key(request)
        auth_route = request.url.path.endswith(("/auth/login", "/auth/register"))
        limit = 10 if auth_route else self.requests_per_minute
        bucket = "auth" if auth_route else "api"
        allowed = False
        try:
            if self._redis is None:
                self._redis = redis.from_url(
                    settings.REDIS_URL, socket_connect_timeout=1, socket_timeout=1
                )
            count = await self._redis.eval(
                """
                local n=redis.call('INCR',KEYS[1])
                if n==1 then redis.call('EXPIRE',KEYS[1],ARGV[1]) end
                return n
            """,
                1,
                "rag:rate:" + bucket + ":" + hashlib.sha256(key.encode()).hexdigest(),
                self.window_seconds,
            )
            allowed = count <= limit
        except Exception:
            if settings.ENVIRONMENT == "production":
                return JSONResponse(
                    {"detail": "Rate limiting service unavailable"}, status_code=503
                )
            now = time.monotonic()
            item_key = (bucket, key)
            entries = [
                ts
                for ts in self._history.pop(item_key, [])
                if ts > now - self.window_seconds
            ]
            allowed = len(entries) < limit
            if allowed:
                entries.append(now)
            self._history[item_key] = entries
            while len(self._history) > 10000:
                self._history.popitem(last=False)
        if not allowed:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Please retry later."},
                status_code=429,
                headers={"Retry-After": str(self.window_seconds)},
            )
        return await call_next(request)
