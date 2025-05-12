from pydantic import BaseModel
from typing import List

class TestResponseBase(BaseModel):
    test_id: int
    student_id: str
    score: int
    responses: List[int]
    wrong_questions: List[int] = []

class TestResponseCreate(TestResponseBase):
    pass

class TestResponse(TestResponseBase):
    id: int

    model_config = {
        "from_attributes": True
    }

