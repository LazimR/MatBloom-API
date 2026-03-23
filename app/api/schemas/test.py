"""
    Este módulo contém os modelos de dados para o Teste.

    classes:
        - TestBase: Modelo base para o Teste.
        - TestCreate: Modelo para criação de um novo Teste.
        - Test: Modelo para retorno de um Teste existente.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field
from typing import List

from app.core.academic import TestKind, TestTargetType, TestVisibility
from .question import Question

class TestBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Teste.

        - Attributes:
            - name: str - Nome do teste.
            - questions: List[int] - Lista de IDs das questões associadas ao teste.
    """
    name: str
    theme: str
    questions: List[int]


class TestCreate(TestBase):
    application_date: date | None = None
    created_by_user_id: int | None = None
    visibility: TestVisibility = TestVisibility.LIBRARY
    target_type: TestTargetType = TestTargetType.INDIVIDUAL


class TestApplicationCreate(BaseModel):
    classroom_id: int
    application_date: date | None = None
    target_type: TestTargetType = TestTargetType.CLASS
    name: str | None = None

class Test(TestBase):
    """
        Esta classe representa o modelo de Teste para retorno.

        - Attributes:
            - id: int - ID do teste.
            - name: str - Nome do teste.
            - questions: List[Question] - Lista de questões associadas ao teste.
    """
    id: int
    kind: TestKind = TestKind.TEMPLATE
    visibility: TestVisibility | None = None
    classroom_id: int | None = None
    source_test_id: int | None = None
    created_by_user_id: int | None = None
    applied_by_user_id: int | None = None
    created_at: datetime
    application_date: date | None = None
    target_type: TestTargetType = TestTargetType.INDIVIDUAL
    questions: List[Question] = Field(default_factory=list)

    model_config = {
        "from_attributes": True
    }
