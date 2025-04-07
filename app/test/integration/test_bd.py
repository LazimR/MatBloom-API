from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db.models.connection import get_session

router = APIRouter()

@router.get("/health")
def health_check(db: Session = Depends(get_session)):
    try:
        # Executa um comando SQL simples para testar a conexão
        db.execute(text("SELECT 1"))
        return {"status": "OK", "database": "connected"}
    except Exception as e:
        return {"status": "Error", "database": "disconnected", "error": str(e)}