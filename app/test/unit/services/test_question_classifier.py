import asyncio

import pytest

from app.api.services import question_classifier


def test_load_questions_from_payload_accepts_list_and_object():
    questions_list = [{"enunciation": "Q1", "itens": ["A", "B"], "correct_item": 0, "level": 0, "contents": ["X"]}]
    questions_object = {"questions": questions_list}

    assert question_classifier.load_questions_from_payload(questions_list) == questions_list
    assert question_classifier.load_questions_from_payload(questions_object) == questions_list


def test_load_questions_from_payload_rejects_invalid_format():
    with pytest.raises(Exception, match="lista de questões"):
        question_classifier.load_questions_from_payload({"items": []})


def test_classify_questions_batch_skips_already_classified(monkeypatch):
    questions = [
        {
            "enunciation": "Questão já classificada",
            "itens": ["A", "B", "C", "D"],
            "correct_item": 1,
            "level": 2,
            "contents": ["Conteúdo"],
        },
        {
            "enunciation": "Questão pendente",
            "itens": ["A", "B", "C", "D"],
            "correct_item": 0,
            "level": 0,
            "contents": ["Outro conteúdo"],
        },
    ]

    async def fake_call(_prompt: str, provider=None):
        return {"classifications": [{"index": 0, "level": 3}]}

    monkeypatch.setattr(question_classifier, "_call_classification_api", fake_call)

    result = asyncio.run(question_classifier.classify_questions_batch(questions))

    assert result[0]["level"] == 2
    assert result[1]["level"] == 3


def test_classify_questions_batch_validates_model_response(monkeypatch):
    questions = [
        {
            "enunciation": "Questão pendente",
            "itens": ["A", "B", "C", "D"],
            "correct_item": 0,
            "level": 0,
            "contents": ["Conteúdo"],
        }
    ]

    async def fake_call(_prompt: str, provider=None):
        return {"classifications": [{"index": 0, "level": 9}]}

    monkeypatch.setattr(question_classifier, "_call_classification_api", fake_call)

    with pytest.raises(Exception, match="nível Bloom inválido"):
        asyncio.run(question_classifier.classify_questions_batch(questions))
