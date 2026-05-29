from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.db.repositories.test_response_repository import TestResponseRepository
from app.api.schemas.test_response import TestResponseCreate
from app.db.models.connection import get_session
from app.api.services.answer_sheet_corrector import answer_sheet_corrector as process_answer_sheet
from app.api.security.auth import get_current_user_payload, ensure_test_scope, require_academic_staff

router = APIRouter()

@router.post("/answer_sheet")
def submit_answer_sheet(
    test_id: int,
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
    _authorized: dict = Depends(require_academic_staff),
):
    """
    Correção de folha de respostas.

    props:
        - image: UploadFile - Imagem da folha de respostas a ser corrigida.
        - test_id: int - ID do teste associado à folha de respostas.
    """

    ensure_test_scope(test_id, session, current_user)

    result = process_answer_sheet(image.file, test_id, session)
    
    response = TestResponseCreate(
        test_id=test_id,
        student_id=int(result[2]),
        score=result[1],
        responses=result[0],
        wrong_questions=result[3]
    )

    test_response_repo = TestResponseRepository(session)
    test_response = test_response_repo.create_test_response(response)


    return test_response
