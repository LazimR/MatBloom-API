import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.endpoints import question as endpoint
from app.api.schemas.question import QuestionCreate, QuestionLevelUpdate


def payload(**extra):
    return {"enunciation": "Quanto é 2 + 2?", "itens": ["3", "4"], "correct_item": 1, "contents": ["Adição"], **extra}


def test_create_classifies_before_saving(monkeypatch):
    async def classify(questions):
        assert questions[0]["enunciation"] == "Quanto é 2 + 2?"
        return [{"level": 3}]

    monkeypatch.setattr(endpoint, "classify_questions_batch", classify)
    monkeypatch.setattr(endpoint, "QuestionRepository", lambda db: SimpleNamespace(create_question=lambda question: question))
    result = asyncio.run(endpoint.create_question(QuestionCreate(**payload()), db=None))
    assert result.level == 3


def test_failed_classification_does_not_save(monkeypatch):
    async def classify(questions):
        raise RuntimeError("indisponível")

    monkeypatch.setattr(endpoint, "classify_questions_batch", classify)
    monkeypatch.setattr(endpoint, "QuestionRepository", lambda db: pytest.fail("Não deve salvar"))
    with pytest.raises(HTTPException) as error:
        asyncio.run(endpoint.create_question(QuestionCreate(**payload()), db=None))
    assert error.value.status_code == 503


def test_existing_api_can_still_create_explicit_level(monkeypatch):
    monkeypatch.setattr(endpoint, "QuestionRepository", lambda db: SimpleNamespace(create_question=lambda question: question))
    result = asyncio.run(endpoint.create_question(QuestionCreate(**payload(level=2)), db=None))
    assert result.level == 2


def test_corrected_level_must_be_classified():
    assert QuestionLevelUpdate(level=6).level == 6
    with pytest.raises(ValidationError):
        QuestionLevelUpdate(level=0)
