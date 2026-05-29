from io import BytesIO
from types import SimpleNamespace

import pytest

from app.api.services import test_generate as test_generate_service
from app.core.exceptions import ValidationError


def test_test_generate_requires_application_kind(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return SimpleNamespace(
                kind="template",
                name="Modelo de prova",
                questions=[],
            )

    monkeypatch.setattr(test_generate_service, "TestRepository", FakeRepository)

    with pytest.raises(ValidationError, match="aplicação de prova"):
        test_generate_service.test_generate(5, ["Maria"], ["7"], db=None)


def test_test_generate_requires_matching_student_names_and_ids(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return SimpleNamespace(
                kind="application",
                name="Aplicacao 1",
                questions=[
                    SimpleNamespace(
                        dict=lambda: {
                            "enunciation": "Questao 1",
                            "itens": ["A", "B", "C"],
                        }
                    )
                ],
            )

    monkeypatch.setattr(test_generate_service, "TestRepository", FakeRepository)

    with pytest.raises(ValidationError, match="quantidade de IDs"):
        test_generate_service.test_generate(5, ["Maria", "Joao"], ["7"], db=None)


def test_test_generate_builds_zip_for_application(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return SimpleNamespace(
                kind="application",
                name="Aplicacao 1",
                questions=[
                    SimpleNamespace(
                        dict=lambda: {
                            "enunciation": "Questao 1",
                            "itens": ["A", "B", "C"],
                        }
                    )
                ],
            )

    monkeypatch.setattr(test_generate_service, "TestRepository", FakeRepository)
    monkeypatch.setattr(
        test_generate_service,
        "pdf_test_generate",
        lambda *_args, **_kwargs: BytesIO(b"test-pdf"),
    )
    monkeypatch.setattr(
        test_generate_service,
        "generate_answer_sheet",
        lambda *_args, **_kwargs: BytesIO(b"answer-sheet"),
    )

    zip_buffer = test_generate_service.test_generate(5, ["Maria"], ["7"], db=None)

    assert zip_buffer.getvalue()


def test_test_generate_requires_target_student_for_individual_application(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return SimpleNamespace(
                kind="application",
                target_type="individual",
                student_id=8,
                name="Aplicacao Individual",
                questions=[
                    SimpleNamespace(
                        dict=lambda: {
                            "enunciation": "Questao 1",
                            "itens": ["A", "B", "C"],
                        }
                    )
                ],
            )

    monkeypatch.setattr(test_generate_service, "TestRepository", FakeRepository)

    with pytest.raises(ValidationError, match="aluno-alvo"):
        test_generate_service.test_generate(5, ["Maria"], ["7"], db=None)
