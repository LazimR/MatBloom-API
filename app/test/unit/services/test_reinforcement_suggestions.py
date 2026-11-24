from types import SimpleNamespace as NS

import pytest
from app.api.services.reinforcement_suggestions import rank_questions
from app.api.services.analysis_service import get_student_analysis
from app.core.exceptions import ValidationError


def question(id, level, alternatives, *contents):
    return NS(id=id, level=level, itens=["x"] * alternatives, contents=[NS(name=name) for name in contents])


def test_prioritizes_content_errors_and_uses_compatible_answer_sheets():
    questions = [question(1, 2, 4, "Frações"), question(2, 3, 4, "Potências"), question(3, 3, 5, "Frações")]
    result = rank_questions(questions, [NS(content_name="Frações", wrong_count=5), NS(content_name="Potências", wrong_count=1)], [NS(level=3, wrong_count=2)], 2)
    assert [item["id"] for item in result] == [1, 2]
    assert result[0]["matched_contents"] == ["Frações"]


def test_no_confirmed_errors_does_not_invent_suggestion():
    with pytest.raises(ValidationError, match="ordem confirmada"):
        rank_questions([question(1, 1, 4, "Frações")], [], [], 1)


def test_excludes_legacy_attempts_from_question_analysis(monkeypatch):
    q = question(1, 1, 4, "Frações")
    old = NS(question_order_confirmed=False, questions=[q], name="Antiga")
    response = NS(test=old, test_id=1, score=5, wrong_questions=[1])
    student = NS(id=1, name="Ana", classroom_id=1, test_responses=[response])
    monkeypatch.setattr("app.api.services.analysis_service._get_student_with_analysis_context", lambda *_: student)
    result = get_student_analysis(None, 1)
    assert result.overall_average == 5
    assert result.unordered_attempts == 1
    assert result.errors_by_content == []
    assert result.bloom_performance[0].total_questions == 0
