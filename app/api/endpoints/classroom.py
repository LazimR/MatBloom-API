from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas.analysis import ClassroomAnalysis
from app.api.schemas.classroom import Classroom, ClassroomCreate, ClassroomUpdate
from app.api.services.analysis_service import get_classroom_analysis
from app.api.security.auth import (
    ensure_classroom_scope,
    get_accessible_classroom_ids,
    get_current_user_payload,
    require_director_or_admin,
    require_user,
)
from app.db.models.connection import get_session
from app.db.repositories.classroom_repository import ClassroomRepository

router = APIRouter()


@router.post("/", response_model=Classroom, dependencies=[Depends(require_director_or_admin)])
def create_classroom(classroom: ClassroomCreate, db: Session = Depends(get_session)):
    repo = ClassroomRepository(db)
    return repo.create_classroom(classroom)


@router.get("/", response_model=list[Classroom], dependencies=[Depends(require_user)])
def list_classrooms(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = ClassroomRepository(db)
    classroom_ids = get_accessible_classroom_ids(db, current_user)
    return repo.list_classrooms(classroom_ids)


@router.get("/{classroom_id}", response_model=Classroom, dependencies=[Depends(require_user)])
def get_classroom(
    classroom_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_classroom_scope(classroom_id, db, current_user)
    repo = ClassroomRepository(db)
    return repo.get_classroom(classroom_id)


@router.get("/{classroom_id}/analysis", response_model=ClassroomAnalysis, dependencies=[Depends(require_user)])
def get_classroom_pedagogical_analysis(
    classroom_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_classroom_scope(classroom_id, db, current_user)
    return get_classroom_analysis(db, classroom_id)


@router.put("/", response_model=Classroom, dependencies=[Depends(require_director_or_admin)])
def update_classroom(classroom: ClassroomUpdate, db: Session = Depends(get_session)):
    repo = ClassroomRepository(db)
    return repo.update_classroom(classroom)


@router.delete("/{classroom_id}", response_model=bool, dependencies=[Depends(require_director_or_admin)])
def delete_classroom(classroom_id: int, db: Session = Depends(get_session)):
    repo = ClassroomRepository(db)
    return repo.delete_classroom(classroom_id)
