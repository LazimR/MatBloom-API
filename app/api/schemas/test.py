"""
    Este módulo contém os modelos de dados para o Teste.

    classes:
        - TestBase: Modelo base para o Teste.
        - TestCreate: Modelo para criação de um novo Teste.
        - Test: Modelo para retorno de um Teste existente.
"""

from pydantic import BaseModel
from .question import Question
from typing import List

class TestBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Teste.

        - Attributes:
            - name: str - Nome do teste.
            - questions: List[int] - Lista de IDs das questões associadas ao teste.
    """
    name: str
    questions: List[int]

class TestCreate(TestBase):
    """
        Esta classe representa o modelo de Teste para criação.

        - Attributes:
            - name: str - Nome do teste.
            - questions: List[int] - Lista de IDs das questões associadas ao teste.
    """

    pass

class Test(TestBase):
    """
        Esta classe representa o modelo de Teste para retorno.

        - Attributes:
            - id: int - ID do teste.
            - name: str - Nome do teste.
            - questions: List[Question] - Lista de questões associadas ao teste.
    """
    id: int
    #name: str
    #questions: List[Question]

    model_config = {
        "from_attributes": True
    }