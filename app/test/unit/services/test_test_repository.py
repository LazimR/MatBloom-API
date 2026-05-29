from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.api.schemas.test import TestApplicationCreate as ApplySchema
from app.api.schemas.test import TestTemplateVersionCreate as VersionSchema
from app.core.exceptions import NotFoundError, ValidationError
from app.db.repositories.test_repository import TestRepository as ExamRepository


class FakeQuery:
    def __init__(self, first_result=None):
        self.first_result = first_result

    def options(self, *_args, **_kwargs):
        return self

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def first(self):
        return self.first_result


class FakeSession:
    def __init__(self, query_results):
        self.query_results = list(query_results)
        self.added = []

    def query(self, _model):
        result = self.query_results.pop(0) if self.query_results else None
        return FakeQuery(first_result=result)

    def add(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 100 + len(self.added)
        self.added.append(obj)

    def flush(self):
        pass

    def commit(self):
        pass


def _question(question_id: int):
    return SimpleNamespace(
        id=question_id,
        enunciation=f"Questao {question_id}",
        itens=["A", "B", "C", "D", "E"],
        correct_item=0,
        level=1,
        contents=[],
        dependencies=[],
        created_at=datetime(2026, 4, 1, 10, 0, 0),
    )


def _template():
    return SimpleNamespace(
        id=5,
        kind="template",
        name="Template Expo",
        theme="Exponenciacao",
        template_group_id=5,
        version_number=1,
        visibility="library",
        target_type="turma",
        created_by_user_id=2,
        questions=[_question(1), _question(2)],
    )


def test_apply_test_requires_student_for_individual_application(monkeypatch):
    session = FakeSession([])
    repo = ExamRepository(session)
    monkeypatch.setattr(repo, "_get_test_model", lambda _test_id: _template())

    with pytest.raises(ValidationError, match="student_id"):
        repo.apply_test(
            5,
            ApplySchema(target_type="individual", application_date=date(2026, 4, 2)),
            applied_by_user_id=2,
        )


def test_apply_test_individual_derives_classroom_from_student(monkeypatch):
    student = SimpleNamespace(id=7, classroom_id=3)
    session = FakeSession([student, _question(1), _question(2), None])
    repo = ExamRepository(session)
    monkeypatch.setattr(repo, "_get_test_model", lambda _test_id: _template())
    monkeypatch.setattr(repo, "get_test", lambda test_id: SimpleNamespace(id=test_id, student_id=7, classroom_id=3))

    result = repo.apply_test(
        5,
        ApplySchema(
            target_type="individual",
            student_id=7,
            application_date=date(2026, 4, 2),
            name="Aplicacao Individual",
        ),
        applied_by_user_id=2,
    )

    created_application = session.added[0]
    assert created_application.student_id == 7
    assert created_application.classroom_id == 3
    assert result.student_id == 7


def test_apply_test_individual_raises_when_student_missing(monkeypatch):
    session = FakeSession([None])
    repo = ExamRepository(session)
    monkeypatch.setattr(repo, "_get_test_model", lambda _test_id: _template())

    with pytest.raises(NotFoundError, match="Student with ID 7"):
        repo.apply_test(
            5,
            ApplySchema(
                target_type="individual",
                student_id=7,
                application_date=date(2026, 4, 2),
            ),
            applied_by_user_id=2,
        )


def test_create_template_version_increments_version(monkeypatch):
    session = FakeSession([(1,), _question(1), _question(2)])
    repo = ExamRepository(session)
    monkeypatch.setattr(repo, "_get_test_model", lambda _test_id: _template())
    monkeypatch.setattr(repo, "get_test", lambda test_id: SimpleNamespace(id=test_id, version_number=2, template_group_id=5))

    result = repo.create_template_version(
        5,
        VersionSchema(name="Template Expo v2", questions=[1, 2]),
        created_by_user_id=9,
    )

    created_template = session.added[0]
    assert created_template.template_group_id == 5
    assert created_template.version_number == 2
    assert result.version_number == 2


def test_get_library_usage_metrics_aggregates_template_usage(monkeypatch):
    session = FakeSession([])
    repo = ExamRepository(session)

    template_expo = SimpleNamespace(
        id=5,
        name="Template Expo",
        theme="Exponenciacao",
        template_group_id=5,
        version_number=2,
        visibility="library",
        questions=[_question(1), SimpleNamespace(**{**_question(2).__dict__, "level": 3})],
    )
    template_fracoes = SimpleNamespace(
        id=8,
        name="Template Fracoes",
        theme="Fracoes",
        template_group_id=8,
        version_number=1,
        visibility="shared",
        questions=[SimpleNamespace(**{**_question(3).__dict__, "level": 2})],
    )

    applications = [
        SimpleNamespace(
            source_test_id=5,
            applied_by_user_id=9,
            application_date=date(2026, 4, 1),
            target_type="turma",
        ),
        SimpleNamespace(
            source_test_id=5,
            applied_by_user_id=10,
            application_date=date(2026, 4, 3),
            target_type="individual",
        ),
    ]

    monkeypatch.setattr(
        repo,
        "_get_accessible_template_models",
        lambda current_user=None, accessible_classroom_ids=None: [template_expo, template_fracoes],
    )
    monkeypatch.setattr(repo, "_get_template_application_models", lambda template_ids: applications)

    metrics = repo.get_library_usage_metrics(
        current_user={"role": "professor", "user_id": 9},
        accessible_classroom_ids={1},
    )

    assert metrics.total_templates == 2
    assert metrics.used_templates == 1
    assert metrics.unused_templates == 1
    assert metrics.total_applications == 2
    assert metrics.templates_with_individual_applications == 1

    first_template = metrics.templates[0]
    assert first_template.template_id == 5
    assert first_template.application_count == 2
    assert first_template.distinct_teacher_count == 2
    assert first_template.classroom_application_count == 1
    assert first_template.individual_application_count == 1
    assert first_template.last_applied_at == date(2026, 4, 3)
    assert first_template.is_unused is False
    assert [item.level for item in first_template.bloom_level_distribution] == [1, 3]
    assert [item.application_count for item in first_template.bloom_level_distribution] == [2, 2]

    second_template = metrics.templates[1]
    assert second_template.template_id == 8
    assert second_template.application_count == 0
    assert second_template.is_unused is True

    assert metrics.theme_distribution[0].theme == "Exponenciacao"
    assert metrics.theme_distribution[0].application_count == 2
    assert metrics.theme_distribution[1].theme == "Fracoes"
    assert metrics.theme_distribution[1].application_count == 0

    assert [item.level for item in metrics.bloom_level_distribution] == [1, 2, 3]
    assert [item.application_count for item in metrics.bloom_level_distribution] == [2, 0, 2]


def test_get_library_usage_metrics_raises_when_no_templates(monkeypatch):
    session = FakeSession([])
    repo = ExamRepository(session)

    monkeypatch.setattr(
        repo,
        "_get_accessible_template_models",
        lambda current_user=None, accessible_classroom_ids=None: [],
    )

    with pytest.raises(NotFoundError, match="No test templates found"):
        repo.get_library_usage_metrics(current_user={"role": "admin", "user_id": 1})
