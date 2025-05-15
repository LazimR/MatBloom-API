from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.models.connection import get_session
from app.db.repositories.test_repository import TestRepository
from app.api.schemas.test import Test, TestCreate
from app.api.schemas.question import Question
from app.api.services.test_generate import test_generate

router = APIRouter()

@router.post("/tests", response_model=Test)
def create_test(test: TestCreate, db: Session = Depends(get_session)):
    """
    Cria um novo teste no banco de dados.
    
    props:
        - test: TestCreate - Dados do teste a ser criado.
        - db: Session - Sessão do banco de dados.

    return:
        - Test - O teste criado.
    """
    repo = TestRepository(db)
    return repo.create_test(test)

@router.get("/tests", response_model=list[Test])
def get_all_tests(db: Session = Depends(get_session)):
    """
    Retorna todos os testes do banco de dados.

    props:
        - db: Session - Sessão do banco de dados.

    return:
        - list[Test] - Lista de todos os testes.
    """
    repo = TestRepository(db)
    return repo.get_all_tests()

@router.get("/tests/{test_id}", response_model=list[Question])
def get_test(test_id: int, db: Session = Depends(get_session)):
    """
    Retorna um teste específico do banco de dados.

    props:
        - test_id: int - ID do teste a ser retornado.
        - db: Session - Sessão do banco de dados.

    return:
        - Test - O teste solicitado.
    """
    repo = TestRepository(db)
    return repo.get_test(test_id)

@router.delete("/tests/{test_id}", response_model=bool)
def delete_test(test_id: int, db: Session = Depends(get_session)):
    """
    Deleta um teste do banco de dados.

    props:
        - test_id: int - ID do teste a ser deletado.
        - db: Session - Sessão do banco de dados.

    return:
        - bool - True se o teste foi deletado com sucesso, False caso contrário.
    """
    repo = TestRepository(db)
    return repo.delete_test(test_id)

@router.get("/tests-generate")
def generate_test(
    test_id: int = Header(...), 
    student_name: str = Header(...,example="Lazaro Claubert,Mauricio Benjamin,Pedro Vital"), 
    student_id: str = Header(..., example="1,2,3"), 
    db: Session = Depends(get_session)
):
    """
    Gera um teste em PDF para o aluno.

    props:
        - test_id: int - ID do teste a ser gerado.
        - student_name: str - Nome do aluno.
        - student_id: int - ID do aluno.
        - db: Session - Sessão do banco de dados.

    return:
        - StreamingResponse - Arquivo ZIP contendo os PDFs gerados.
    """
    try:
        # Divide os nomes e IDs dos alunos em listas
        student_names = student_name.split(",")
        student_ids = student_id.split(",")

        # Chama a função para gerar os PDFs
        zip_buffer = test_generate(test_id, student_names, student_ids, db)

        # Retorna o arquivo ZIP como resposta
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=testes.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))