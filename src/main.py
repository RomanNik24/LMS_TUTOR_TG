from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.auth import router as auth_router
from src.api.students import router as students_router
from src.api.webapp import router as webapp_router
from src.core.config import settings


def create_app() -> FastAPI:
    """Фабрика приложения (используется uvicorn-ом и тестами)."""
    app = FastAPI(
        title="MY_LMS API",
        description="API для системы управления обучением",
        version="1.0.0",
    )

    # CORS: Flet-сервер и браузер Telegram calls API с других origin'ов
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.api_base_url,
            "http://127.0.0.1:8550",
            "http://localhost:8550",
            "http://webapp:8550",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router)
    app.include_router(students_router)
    app.include_router(webapp_router)

    @app.get("/")
    async def root():
        return {"message": "Welcome to MY_LMS API"}

    return app


app = create_app()