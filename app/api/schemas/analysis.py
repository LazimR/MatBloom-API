from typing import Any

from pydantic import BaseModel, Field

from app.core.academic import TestKind, TestTargetType


class BloomPerformanceItem(BaseModel):
    level: int
    level_name: str
    total_questions: int
    correct_answers: int
    wrong_answers: int
    accuracy: float


class BloomErrorItem(BaseModel):
    level: int
    level_name: str
    wrong_count: int


class ContentErrorItem(BaseModel):
    content_name: str
    wrong_count: int


class TestAverageItem(BaseModel):
    test_id: int
    test_name: str
    average_score: float
    attempts: int


class StudentAverageItem(BaseModel):
    student_id: int
    student_name: str
    average_score: float | None
    attempts: int


class StudentAnalysis(BaseModel):
    student_id: int
    student_name: str
    classroom_id: int
    overall_average: float | None
    total_attempts: int
    average_by_test: list[TestAverageItem] = Field(default_factory=list)
    bloom_performance: list[BloomPerformanceItem] = Field(default_factory=list)
    errors_by_content: list[ContentErrorItem] = Field(default_factory=list)
    errors_by_bloom: list[BloomErrorItem] = Field(default_factory=list)


class ClassroomAnalysis(BaseModel):
    classroom_id: int
    classroom_name: str
    school_year: int
    grade_level: str
    shift: str
    student_count: int
    active_students: int
    overall_average: float | None
    average_by_test: list[TestAverageItem] = Field(default_factory=list)
    bloom_performance: list[BloomPerformanceItem] = Field(default_factory=list)
    errors_by_content: list[ContentErrorItem] = Field(default_factory=list)
    errors_by_bloom: list[BloomErrorItem] = Field(default_factory=list)
    student_averages: list[StudentAverageItem] = Field(default_factory=list)


class ReinforcementQuestion(BaseModel):
    enunciation: str
    itens: list[str] = Field(default_factory=list)
    correct_item: int
    level: int
    level_name: str
    contents: list[str] = Field(default_factory=list)


class ReinforcementGeneratedTest(BaseModel):
    id: int
    name: str
    kind: TestKind
    target_type: TestTargetType


class StudentReinforcement(BaseModel):
    student_id: int
    student_name: str
    source_question_count: int
    generated_question_count: int = 0
    generated_reinforcement: dict[str, Any]
    generated_questions: list[ReinforcementQuestion] = Field(default_factory=list)
    created_template: ReinforcementGeneratedTest | None = None
    created_application: ReinforcementGeneratedTest | None = None
    pdf_download_url: str | None = None
