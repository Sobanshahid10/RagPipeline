from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import uuid
import asyncpg


@asynccontextmanager
async def lifespan(app):
    if settings.ENVIRONMENT == "production":
        conn = await asyncpg.connect(
            settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
        )
        try:
            unsafe = await conn.fetchval(
                "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname=current_user"
            )
            if unsafe:
                raise RuntimeError(
                    "Runtime database role must not bypass tenant security"
                )
        finally:
            await conn.close()
    yield


from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.retrieval import router as retrieval_router
from app.api.query import router as query_router
from app.api.admin import router as admin_router
from app.api.public_book import router as public_book_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
)

# ── OpenTelemetry tracing ────────────────────────────────────────────────────
try:
    from app.core.telemetry import setup_telemetry

    _tracer = setup_telemetry(app)
except Exception:
    pass  # Tracing is non-critical; boot without it if deps are missing.

from app.core.security_middleware import (
    RateLimitingMiddleware,
    SecurityHeadersMiddleware,
)

# Security Hardening Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitingMiddleware, requests_per_minute=60, window_seconds=60)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(
    auth_router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"]
)
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(query_router)
app.include_router(admin_router)
app.include_router(public_book_router)


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"


class InfoResponse(BaseModel):
    project: str
    environment: str


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health():
    return HealthResponse(status="healthy", version="1.0.0")


@app.get(f"{settings.API_V1_STR}/info", response_model=InfoResponse, tags=["System"])
async def get_info():
    return InfoResponse(project=settings.PROJECT_NAME, environment=settings.ENVIRONMENT)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging

    request_id = str(uuid.uuid4())
    logging.getLogger("app.main").error(
        "Unhandled request %s on %s %s (%s)",
        request_id,
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    origin = request.headers.get("origin")
    headers = {"Cache-Control": "no-store"}
    if origin in settings.CORS_ORIGINS:
        headers.update({"Access-Control-Allow-Origin": origin, "Vary": "Origin"})
    return JSONResponse(
        headers=headers,
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )
