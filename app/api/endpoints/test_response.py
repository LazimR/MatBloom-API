from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.test_response import TestResponse, TestResponseCreate, TestResponseUpdate
from app.api.security.auth import (
    ensure_student_scope,
    ensure_test_response_scope,
    get_accessible_classroom_ids,
    get_current_user_payload,
    require_academic_staff,
    require_director_or_admin,
    require_user,
)
from app.db.models.connection import get_session
from app.db.repositories.test_response_repository import TestResponseRepository

router = APIRouter()


@router.post("/", response_model=TestResponse, dependencies=[Depends(require_academic_staff)])
def create_test_response(
    test_response: TestResponseCreate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_student_scope(test_response.student_id, db, current_user)
    repo = TestResponseRepository(db)
    return repo.create_test_response(test_response)


@router.get("/", response_model=list[TestResponse], dependencies=[Depends(require_user)])
def list_test_responses(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = TestResponseRepository(db)
    classroom_ids = get_accessible_classroom_ids(db, current_user)
    return repo.get_all_test_responses(classroom_ids)


@router.get("/{test_response_id}", response_model=TestResponse, dependencies=[Depends(require_user)])
def get_test_response(
    test_response_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_test_response_scope(test_response_id, db, current_user)
    repo = TestResponseRepository(db)
    return repo.get_test_response(test_response_id)


@router.put("/", response_model=TestResponse, dependencies=[Depends(require_academic_staff)])
def update_test_response(
    test_response: TestResponseUpdate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_test_response_scope(test_response.id, db, current_user)
    repo = TestResponseRepository(db)
    return repo.update_test_response(test_response)


@router.delete("/{test_response_id}", response_model=bool, dependencies=[Depends(require_director_or_admin)])
def delete_test_response(test_response_id: int, db: Session = Depends(get_session)):
    repo = TestResponseRepository(db)
    deleted = repo.delete_test_response(test_response_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Test response with ID {test_response_id} does not exist.")
    return deleted
