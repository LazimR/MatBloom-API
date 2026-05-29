from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import content
from app.api.endpoints import answer_sheet
from app.api.endpoints import classroom
from app.api.endpoints import student
from app.api.endpoints import test
from app.api.endpoints import test_response
from app.api.endpoints import user
from app.api.endpoints import question

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.core.exceptions import AppError
from app.db.models.connection import get_session


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield


app = FastAPI(lifespan=lifespan)

frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# Inclui os endpoints de conteúdo
app.include_router(content.router, prefix="/content", tags=["Content"])
app.include_router(answer_sheet.router, prefix="/answer-sheet", tags=["Answer Sheet"])
app.include_router(classroom.router, prefix="/classroom", tags=["Classroom"])
app.include_router(student.router, prefix="/student", tags=["Student"])
app.include_router(test.router, prefix="/test", tags=["Test"])
app.include_router(test_response.router, prefix="/test-response", tags=["Test Response"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(question.router, prefix="/question", tags=["Question"])

@app.get("/")
def read_root():
    return {"message": "Welcome to MatBloom API!"}

@app.get("/health")
def health_check(db: Session = Depends(get_session)):
    try:
        # Executa um comando SQL simples para testar a conexão
        db.execute(text("SELECT 1"))
        return {"status": "OK", "database": "connected"}
    except Exception as e:
        return {"status": "Error", "database": "disconnected", "error": str(e)}
