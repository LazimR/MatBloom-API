from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.repositories.content_repository import ContentRepository
from app.api.schemas.content import Content, ContentCreate
from app.db.models.connection import get_session

from app.api.security.auth import require_user

router = APIRouter()

@router.post("/", response_model=Content, dependencies=[Depends(require_user)])
def create_content(content: ContentCreate, db: Session = Depends(get_session)):
    repo = ContentRepository(db)
    return repo.create_content(content)

@router.get("/", response_model=list[Content], dependencies=[Depends(require_user)])
def get_all_contents(db: Session = Depends(get_session)):
    content_repo = ContentRepository(db)
    contents = content_repo.get_all_contents()
    return contents

@router.get("/{content_id}", response_model=Content, dependencies=[Depends(require_user)])
def read_content(content_id: int, db: Session = Depends(get_session)):
    repo = ContentRepository(db)
    return repo.get_content(content_id)

@router.put("/{content_id}", response_model=Content, dependencies=[Depends(require_user)])
def update_content(content_id: int, content: ContentCreate, db: Session = Depends(get_session)):
    repo = ContentRepository(db)
    return repo.update_content(content_id, content)

@router.delete("/{content_id}", response_model=Content, dependencies=[Depends(require_user)])
def delete_content(content_id: int, db: Session = Depends(get_session)):
    repo = ContentRepository(db)
    return repo.delete_content(content_id)
