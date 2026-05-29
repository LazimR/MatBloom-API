from datetime import date
from types import SimpleNamespace

import pytest

from app.api.schemas.test_response import TestResponseCreate as ResponseCreateSchema
from app.core.exceptions import ValidationError
from app.db.models.models import Student as StudentDbModel
from app.db.models.models import Test as ExamDbModel
from app.db.models.models import TestResponse as ResponseDbModel
from app.db.repositories.test_response_repository import TestResponseRepository as ResponseRepo


class FakeQuery:
    def __init__(self, result=None, results=None):
        self.result = result
        self.results = results or []

    def filter(self, *_args, **_kwargs):
        return self

    def join(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.result

    def all(self):
        return self.results


class FakeSession:
    def __init__(self, mapping):
        self.mapping = mapping
        self.added = None

    def query(self, model):
        result = self.mapping.get(model, [])
        if isinstance(result, list):
            return FakeQuery(results=result)
        return FakeQuery(result=result)

    def add(self, obj):
        self.added = obj

    def commit(self):
        pass

    def refresh(self, obj):
        obj.id = 99


def test_create_test_response_requires_application_test():
    session = FakeSession(
        {
            ExamDbModel: SimpleNamespace(id=1, kind="template", classroom_id=None),
            StudentDbModel: SimpleNamespace(id=7, classroom_id=2),
        }
    )
    repo = ResponseRepo(session)

    with pytest.raises(ValidationError, match="aplicação de prova"):
        repo.create_test_response(
            ResponseCreateSchema(
                test_id=1,
                student_id=7,
                score=8.0,
                responses=[0, 1],
                wrong_questions=[2],
                attempt_date=date(2026, 3, 23),
            )
        )


def test_create_test_response_requires_student_from_same_classroom():
    session = FakeSession(
        {
            ExamDbModel: SimpleNamespace(id=1, kind="application", classroom_id=3),
            StudentDbModel: SimpleNamespace(id=7, classroom_id=2),
        }
    )
    repo = ResponseRepo(session)

    with pytest.raises(ValidationError, match="mesma turma"):
        repo.create_test_response(
            ResponseCreateSchema(
                test_id=1,
                student_id=7,
                score=8.0,
                responses=[0, 1],
                wrong_questions=[2],
                attempt_date=date(2026, 3, 23),
            )
        )


def test_create_test_response_accepts_application_for_same_classroom():
    session = FakeSession(
        {
            ExamDbModel: SimpleNamespace(id=1, kind="application", classroom_id=2),
            StudentDbModel: SimpleNamespace(id=7, classroom_id=2),
        }
    )
    repo = ResponseRepo(session)

    response = repo.create_test_response(
        ResponseCreateSchema(
            test_id=1,
            student_id=7,
            score=8.0,
            responses=[0, 1],
            wrong_questions=[2],
            attempt_date=date(2026, 3, 23),
        )
    )

    assert response.id == 99
    assert session.added.test_id == 1
    assert session.added.student_id == 7


def test_create_test_response_requires_target_student_for_individual_application():
    session = FakeSession(
        {
            ExamDbModel: SimpleNamespace(
                id=1,
                kind="application",
                classroom_id=2,
                target_type="individual",
                student_id=8,
            ),
            StudentDbModel: SimpleNamespace(id=7, classroom_id=2),
        }
    )
    repo = ResponseRepo(session)

    with pytest.raises(ValidationError, match="aluno-alvo"):
        repo.create_test_response(
            ResponseCreateSchema(
                test_id=1,
                student_id=7,
                score=8.0,
                responses=[0, 1],
                wrong_questions=[2],
                attempt_date=date(2026, 4, 1),
            )
        )


def test_get_test_response_rejects_response_from_non_application_test():
    db_test_response = SimpleNamespace(
        id=10,
        test_id=1,
        student_id=7,
        score=8.0,
        responses=[0, 1],
        wrong_questions=[2],
        attempt_date=date(2026, 3, 23),
        test=SimpleNamespace(kind="template"),
    )
    session = FakeSession({ResponseDbModel: db_test_response})
    repo = ResponseRepo(session)

    with pytest.raises(ValidationError, match="não é uma aplicação|nao é uma aplicação"):
        repo.get_test_response(10)
