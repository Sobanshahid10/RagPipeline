from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings
from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.retrieval import router as retrieval_router
from app.api.query import router as query_router
from app.api.admin import router as admin_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs"
)

# ── OpenTelemetry tracing ────────────────────────────────────────────────────
try:
    from app.core.telemetry import setup_telemetry
    _tracer = setup_telemetry(app)
except Exception:
    pass  # Tracing is non-critical; boot without it if deps are missing.

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_STR}/auth",
    tags=["Authentication"]
)
app.include_router(documents_router)
app.include_router(retrieval_router)
app.include_router(query_router)
app.include_router(admin_router)


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
    return InfoResponse(
        project=settings.PROJECT_NAME,
        environment="development"
    )
