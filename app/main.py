from fastapi import FastAPI, Depends
from app.api.endpoints import content

from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.models.connection import get_session

app = FastAPI()

# Inclui os endpoints de conteúdo
app.include_router(content.router, prefix="/api", tags=["contents"])

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