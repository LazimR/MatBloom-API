from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse

from app.db.repositories.test_response_repository import TestResponseRepository
from app.api.schemas.test_response import TestResponse, TestResponseCreate
from app.db.models.connection import get_session
from app.api.services.answer_sheet_corrector import answer_sheet_corrector

router = APIRouter()

@router.post("/answer_sheet")
def answer_sheet_corrector(
    test_id: int,
    image: UploadFile = File(...),
    session=Depends(get_session)
):
    """
    Correção de folha de respostas.

    props:
        - image: UploadFile - Imagem da folha de respostas a ser corrigida.
        - test_id: int - ID do teste associado à folha de respostas.
    """

    result = answer_sheet_corrector(image.file, test_id)

    if not result:
        raise HTTPException(status_code=400, detail="Erro ao corrigir a folha de respostas.")
    
    response = TestResponseCreate(
        test_id=test_id,
        student_id=result[2],
        score=result[1],
        responses=result[0],
        wrong_questions=result[3]
    )

    test_response_repo = TestResponseRepository(session)
    test_response = test_response_repo.create_test_response(response)


    return result