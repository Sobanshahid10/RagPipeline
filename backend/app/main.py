from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs"
)

# Enable CORS for Next.js Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthCheck(BaseModel):
    status: str = "healthy"
    version: str = "1.0.0"

@app.get("/health", response_model=HealthCheck, tags=["Health"])
async def get_health():
    return HealthCheck(status="healthy", version="1.0.0")

@app.get(f"{settings.API_V1_STR}/info", tags=["System"])
async def get_system_info():
    return {
        "project": settings.PROJECT_NAME,
        "environment": "production-grade-stage-1",
        "database": "PostgreSQL + pgvector",
        "cache": "Redis Vector Cache"
    }
