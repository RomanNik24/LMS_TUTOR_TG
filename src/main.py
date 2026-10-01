from fastapi import FastAPI

from src.api.auth import router as auth_router
from src.api.students import router as students_router
from src.db.session import lifespan


app = FastAPI(
    title="MY_LMS API",
    description="API для системы управления обучением",
    version="1.0.0",
    lifespan=lifespan,
)


app.include_router(auth_router)
app.include_router(students_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to MY_LMS API"
    }