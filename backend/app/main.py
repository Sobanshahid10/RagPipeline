from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
