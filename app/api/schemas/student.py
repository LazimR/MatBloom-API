from datetime import datetime
from typing import List

from pydantic import BaseModel, Field

from app.api.schemas.test_response import TestResponse

class StudentBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Estudante.

        - Attributes:
            - name: str - Nome do estudante.
            - email: str - Endereço de e-mail do estudante.
            - password: str - Senha do estudante.
    """
    name: str
    registration: str
    classroom_id: int
    active: bool = True

class StudentCreate(StudentBase):
    """
        Esta classe representa o modelo de Estudante para criação.

        - Attributes:
            - name: str - Nome do estudante.
            - email: str - Endereço de e-mail do estudante.
            - password: str - Senha do estudante.
    """
    pass


class StudentUpdate(BaseModel):
    id: int
    name: str | None = None
    registration: str | None = None
    classroom_id: int | None = None
    active: bool | None = None

class Student(StudentBase):
    """
        Esta classe representa o modelo de Estudante para retorno.

        - Attributes:
            - id: int - ID do estudante.
            - name: str - Nome do estudante.
            - test_responses: List[TestResponse] - Respostas do estudante.
    """
    id: int
    created_at: datetime
    test_responses: List[TestResponse] = Field(default_factory=list)


    model_config = {
        "from_attributes": True
    }
