from app.api.schemas.test_response import TestResponse
from pydantic import BaseModel
from typing import List

class StudentBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Estudante.

        - Attributes:
            - name: str - Nome do estudante.
            - email: str - Endereço de e-mail do estudante.
            - password: str - Senha do estudante.
    """
    name: str

class StudentCreate(StudentBase):
    """
        Esta classe representa o modelo de Estudante para criação.

        - Attributes:
            - name: str - Nome do estudante.
            - email: str - Endereço de e-mail do estudante.
            - password: str - Senha do estudante.
    """
    pass

class Student(StudentBase):
    """
        Esta classe representa o modelo de Estudante para retorno.

        - Attributes:
            - id: int - ID do estudante.
            - name: str - Nome do estudante.
            - test_responses: List[TestResponse] - Respostas do estudante.
    """
    id: int
    test_responses: List[TestResponse] = []


    class Config:
        orm_mode = True