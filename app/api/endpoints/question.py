from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models.connection import get_session
from app.db.repositories.question_repository import QuestionRepository

from app.api.schemas.question import Question as QuestionSchema, QuestionCreate, QuestionDelete
from app.api.security.auth import require_user

router = APIRouter()

@router.get("/all_questions", response_model=list[QuestionSchema], dependencies=[Depends(require_user)])
def get_all_questions(db: Session = Depends(get_session)):
    """
    Retorna todas as questões do banco de dados.

    props:
        - db: Session - Sessão do banco de dados.

    return:
        - list[Question] - Lista de todas as questões.
    """
    repo = QuestionRepository(db)
    return repo.get_all_questions()

@router.get("/{question_id}", response_model=QuestionSchema, dependencies=[Depends(require_user)])
def get_question(question_id: int, db: Session = Depends(get_session)):
    """
    Retorna uma questão específica do banco de dados.

    props:
        - question_id: int - ID da questão a ser retornada.
        - db: Session - Sessão do banco de dados.

    return:
        - Question - A questão solicitada.
    """
    repo = QuestionRepository(db)
    return repo.get_question(question_id)

@router.post("/", response_model=QuestionSchema, dependencies=[Depends(require_user)])
def create_question(question: QuestionCreate, db: Session = Depends(get_session)):
    """
    Cria uma nova questão no banco de dados.

    props:
        - question: QuestionCreate - Dados da questão a ser criada.
        - db: Session - Sessão do banco de dados.

    return:
        - Question - A questão criada.
    """
    repo = QuestionRepository(db)
    return repo.create_question(question)

@router.delete("/", response_model=bool, dependencies=[Depends(require_user)])
def delete_question(question: QuestionDelete, db: Session = Depends(get_session)):
    """
    Deleta uma questão do banco de dados.

    props:
        - question: QuestionDelete - Dados da questão a ser deletada.
        - db: Session - Sessão do banco de dados.

    return:
        - bool - True se a questão foi deletada com sucesso, False caso contrário.
    """
    repo = QuestionRepository(db)
    return repo.delete_question(question)