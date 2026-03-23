from datetime import date

from pydantic import BaseModel, Field
from typing import List

class TestResponseBase(BaseModel):
    test_id: int
    student_id: int
    score: float
    responses: List[int]
    wrong_questions: List[int] = Field(default_factory=list)
    attempt_date: date = Field(default_factory=date.today)

class TestResponseCreate(TestResponseBase):
    pass


class TestResponseUpdate(BaseModel):
    id: int
    score: float | None = None
    responses: List[int] | None = None
    wrong_questions: List[int] | None = None
    attempt_date: date | None = None

class TestResponse(TestResponseBase):
    id: int

    model_config = {
        "from_attributes": True
    }
