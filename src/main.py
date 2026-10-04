"""Application entry point: FastAPI + Aiogram lifespan."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.v1 import router as api_v1_router
from src.api.health import router as health_router
from src.api.webhook import router as webhook_router
from src.core.config import settings
from src.core.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    setup_logging()
    # Initialize Sentry, Redis, S3 client, Aiogram Dispatcher
    # Set webhook or start polling based on BOT_MODE
    yield
    # Shutdown
    # Close connections, stop polling


def create_app() -> FastAPI:
    app = FastAPI(
        title="MY_LMS API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.APP_ENV != "prod" else None,
        redoc_url="/redoc" if settings.APP_ENV != "prod" else None,
        openapi_url="/openapi.json" if settings.APP_ENV != "prod" else None,
    )

    # CORS not needed in production (same domain via Nginx)
    if settings.APP_ENV == "local":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health_router)
    app.include_router(webhook_router)
    app.include_router(api_v1_router, prefix="/api/v1")

    return app


app = create_app()