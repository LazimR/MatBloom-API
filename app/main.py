from fastapi import FastAPI, Depends
from app.api.endpoints import content
from app.api.endpoints import test
from app.api.endpoints import user
from app.api.endpoints import question

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.models.connection import engine
from app.db.models.connection import get_session
from app.db.models.models import create_entities

app = FastAPI()

# Inclui os endpoints de conteúdo
app.include_router(content.router, prefix="/content", tags=["Content"])
app.include_router(test.router, prefix="/test", tags=["Test"])
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(question.router, prefix="/question", tags=["Question"])

@app.on_event("startup")
def on_startup():
    create_entities(engine)

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