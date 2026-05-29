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
    classroom_id: int | None = None
    student_id: int | None = None
    application_date: date | None = None
    target_type: TestTargetType = TestTargetType.CLASS
    name: str | None = None


class TestTemplateVersionCreate(BaseModel):
    name: str | None = None
    theme: str | None = None
    questions: List[int] | None = None
    visibility: TestVisibility | None = None

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
    student_id: int | None = None
    source_test_id: int | None = None
    template_group_id: int | None = None
    version_number: int = 1
    created_by_user_id: int | None = None
    applied_by_user_id: int | None = None
    created_at: datetime
    application_date: date | None = None
    target_type: TestTargetType = TestTargetType.INDIVIDUAL
    questions: List[Question] = Field(default_factory=list)

    model_config = {
        "from_attributes": True
    }


class TestThemeUsageMetric(BaseModel):
    theme: str
    application_count: int
    template_count: int


class TestBloomLevelUsageMetric(BaseModel):
    level: int
    application_count: int
    question_count: int


class TestTemplateUsageMetric(BaseModel):
    template_id: int
    template_group_id: int | None = None
    version_number: int = 1
    name: str
    theme: str
    visibility: TestVisibility
    application_count: int
    distinct_teacher_count: int
    classroom_application_count: int
    individual_application_count: int
    last_applied_at: date | None = None
    bloom_level_distribution: List[TestBloomLevelUsageMetric] = Field(default_factory=list)
    is_unused: bool


class TestLibraryUsageMetrics(BaseModel):
    total_templates: int
    used_templates: int
    unused_templates: int
    total_applications: int
    templates_with_individual_applications: int
    theme_distribution: List[TestThemeUsageMetric] = Field(default_factory=list)
    bloom_level_distribution: List[TestBloomLevelUsageMetric] = Field(default_factory=list)
    templates: List[TestTemplateUsageMetric] = Field(default_factory=list)
