from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.analysis import StudentAnalysis
from app.api.schemas.student import Student, StudentCreate, StudentUpdate
from app.api.services.analysis_service import get_student_analysis
from app.api.security.auth import (
    ensure_student_scope,
    get_accessible_classroom_ids,
    get_current_user_payload,
    require_director_or_admin,
    require_user,
)
from app.db.models.connection import get_session
from app.db.repositories.student_repository import StudentRepository

router = APIRouter()


@router.post("/", response_model=Student, dependencies=[Depends(require_director_or_admin)])
def create_student(student: StudentCreate, db: Session = Depends(get_session)):
    repo = StudentRepository(db)
    return repo.create_student(student)


@router.get("/", response_model=list[Student], dependencies=[Depends(require_user)])
def list_students(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = StudentRepository(db)
    classroom_ids = get_accessible_classroom_ids(db, current_user)
    return repo.list_students(classroom_ids)


@router.get("/{student_id}", response_model=Student, dependencies=[Depends(require_user)])
def get_student(
    student_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_student_scope(student_id, db, current_user)
    repo = StudentRepository(db)
    return repo.get_student(student_id)


@router.get("/{student_id}/analysis", response_model=StudentAnalysis, dependencies=[Depends(require_user)])
def get_student_pedagogical_analysis(
    student_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_student_scope(student_id, db, current_user)
    return get_student_analysis(db, student_id)


@router.post(
    "/{student_id}/analysis/reinforcement",
    dependencies=[Depends(require_user)],
)
def generate_student_analysis_reinforcement(
    student_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_student_scope(student_id, db, current_user)
    raise HTTPException(
        status_code=410,
        detail=(
            "A geração automática de novas questões e provas foi descontinuada. "
            "Use as rotas de análise do aluno para identificar erros por conteúdo e nível de Bloom."
        ),
    )


@router.put("/", response_model=Student, dependencies=[Depends(require_director_or_admin)])
def update_student(student: StudentUpdate, db: Session = Depends(get_session)):
    repo = StudentRepository(db)
    return repo.update_student(student)


@router.delete("/{student_id}", response_model=bool, dependencies=[Depends(require_director_or_admin)])
def delete_student(student_id: int, db: Session = Depends(get_session)):
    repo = StudentRepository(db)
    return repo.delete_student(student_id)
