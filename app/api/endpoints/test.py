from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.schemas.test import Test, TestApplicationCreate, TestCreate
from app.api.security.auth import (
    ensure_classroom_scope,
    ensure_test_scope,
    get_accessible_classroom_ids,
    get_current_user_payload,
    require_user,
)
from app.api.services.test_generate import test_generate
from app.core.academic import TestKind
from app.db.models.connection import get_session
from app.db.repositories.test_repository import TestRepository

router = APIRouter()


@router.post("/", response_model=Test, dependencies=[Depends(require_user)])
def create_test_template(
    test: TestCreate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = TestRepository(db)
    payload = test.model_copy(
        update={"created_by_user_id": test.created_by_user_id or current_user.get("user_id")}
    )
    return repo.create_test(payload)


@router.post("/{test_id}/apply", response_model=Test, dependencies=[Depends(require_user)])
def apply_test_template_to_classroom(
    test_id: int,
    application: TestApplicationCreate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_test_scope(test_id, db, current_user)
    ensure_classroom_scope(application.classroom_id, db, current_user)
    repo = TestRepository(db)
    return repo.apply_test_to_classroom(test_id, application, current_user.get("user_id"))


@router.get("/", response_model=list[Test], dependencies=[Depends(require_user)])
def get_all_tests(
    kind: str | None = Query(default=None),
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = TestRepository(db)
    classroom_ids = get_accessible_classroom_ids(db, current_user)
    return repo.get_all_tests(
        current_user=current_user,
        accessible_classroom_ids=classroom_ids,
        kind=kind,
    )


@router.get("/templates", response_model=list[Test], dependencies=[Depends(require_user)])
def list_test_templates(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = TestRepository(db)
    classroom_ids = get_accessible_classroom_ids(db, current_user)
    return repo.get_all_tests(
        current_user=current_user,
        accessible_classroom_ids=classroom_ids,
        kind=TestKind.TEMPLATE.value,
    )


@router.get("/applications", response_model=list[Test], dependencies=[Depends(require_user)])
def list_test_applications(
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = TestRepository(db)
    classroom_ids = get_accessible_classroom_ids(db, current_user)
    return repo.get_all_tests(
        current_user=current_user,
        accessible_classroom_ids=classroom_ids,
        kind=TestKind.APPLICATION.value,
    )


@router.get("/test_generate", dependencies=[Depends(require_user)])
def generate_test(
    test_id: int = Header(...),
    student_name: str = Header(..., examples=["Lazaro Claubert,Mauricio Benjamin,Pedro Vital"]),
    student_id: str = Header(..., examples=["1,2,3"]),
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    try:
        ensure_test_scope(test_id, db, current_user)
        student_names = student_name.split(",")
        student_ids = student_id.split(",")

        zip_buffer = test_generate(test_id, student_names, student_ids, db)

        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=testes.zip"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{test_id}", response_model=Test, dependencies=[Depends(require_user)])
def get_test(
    test_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_test_scope(test_id, db, current_user)
    repo = TestRepository(db)
    return repo.get_test(test_id)


@router.delete("/{test_id}", response_model=bool, dependencies=[Depends(require_user)])
def delete_test(
    test_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    ensure_test_scope(test_id, db, current_user)
    repo = TestRepository(db)
    return repo.delete_test(test_id)
