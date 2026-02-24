"""NeuroWeave FastAPI application.

Entry point: uvicorn api.main:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("app_startup", env=settings.APP_ENV)
    yield
    # Shutdown: close DB connections, Redis pool, etc.
    from api.db.session import engine

    await engine.dispose()
    logger.info("app_shutdown")


app = FastAPI(
    title="NeuroWeave API",
    description="Technical knowledge extraction from Discord",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.APP_ENV == "development" else None,
    redoc_url="/redoc" if settings.APP_ENV == "development" else None,
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Exception handlers ---

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


# --- Routers ---

from api.routers.auth import router as auth_router  # noqa: E402
from api.routers.articles import router as articles_router  # noqa: E402
from api.routers.search import router as search_router  # noqa: E402
from api.routers.consent import router as consent_router  # noqa: E402
from api.routers.servers import router as servers_router  # noqa: E402
from api.routers.datasets import router as datasets_router  # noqa: E402
from api.routers.webhooks import router as webhooks_router  # noqa: E402
from api.routers.github import router as github_router  # noqa: E402

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(articles_router, prefix="/api", tags=["articles"])
app.include_router(search_router, prefix="/api", tags=["search"])
app.include_router(consent_router, prefix="/api", tags=["consent"])
app.include_router(servers_router, prefix="/api", tags=["servers"])
app.include_router(datasets_router, prefix="/api", tags=["datasets"])
app.include_router(webhooks_router, prefix="/api", tags=["webhooks"])
app.include_router(github_router, prefix="/api", tags=["github"])


# --- Health check ---

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
