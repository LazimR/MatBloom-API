import asyncio
from datetime import date
from types import SimpleNamespace

import pytest

from app.api.services import analysis_service
from app.core.exceptions import OperationError, ValidationError


def _content(name: str):
    return SimpleNamespace(name=name)


def _question(question_id: int, level: int, enunciation: str, *content_names: str):
    return SimpleNamespace(
        id=question_id,
        level=level,
        enunciation=enunciation,
        contents=[_content(content_name) for content_name in content_names],
    )


def _test(test_id: int, name: str, theme: str, questions: list[SimpleNamespace]):
    return SimpleNamespace(
        id=test_id,
        name=name,
        theme=theme,
        questions=questions,
    )


def _response(
    test_id: int,
    test: SimpleNamespace,
    score: float | None,
    wrong_questions: list[int],
    attempt_date: date,
):
    return SimpleNamespace(
        test_id=test_id,
        test=test,
        score=score,
        wrong_questions=wrong_questions,
        attempt_date=attempt_date,
    )


def test_get_student_analysis_aggregates_scores_bloom_and_content(monkeypatch):
    algebra = _question(1, 1, "Quanto e 2 + 2?", "Adicao")
    geometry = _question(2, 3, "Calcule a area.", "Geometria")
    fractions = _question(3, 2, "Simplifique a fracao.", "Fracoes")

    diagnostic_test = _test(10, "Diagnostica", "Operacoes", [algebra, geometry])
    review_test = _test(20, "Revisao", "Fracoes", [fractions])

    student = SimpleNamespace(
        id=7,
        name="Maria",
        classroom_id=2,
        test_responses=[
            _response(10, diagnostic_test, 7.25, [2], date(2026, 3, 20)),
            _response(10, diagnostic_test, 8.75, [1], date(2026, 3, 21)),
            _response(20, review_test, None, [1], date(2026, 3, 22)),
        ],
    )

    monkeypatch.setattr(
        analysis_service,
        "_get_student_with_analysis_context",
        lambda _db, _student_id: student,
    )

    analysis = analysis_service.get_student_analysis(db=None, student_id=7)

    assert analysis.student_name == "Maria"
    assert analysis.total_attempts == 3
    assert analysis.overall_average == 8.0
    assert [(item.test_id, item.average_score, item.attempts) for item in analysis.average_by_test] == [
        (10, 8.0, 2),
    ]
    assert [(item.level, item.correct_answers, item.wrong_answers, item.accuracy) for item in analysis.bloom_performance] == [
        (1, 1, 1, 50.0),
        (2, 0, 1, 0.0),
        (3, 1, 1, 50.0),
        (4, 0, 0, 0.0),
        (5, 0, 0, 0.0),
        (6, 0, 0, 0.0),
    ]
    assert [(item.content_name, item.wrong_count) for item in analysis.errors_by_content] == [
        ("Adicao", 1),
        ("Fracoes", 1),
        ("Geometria", 1),
    ]
    assert [(item.level, item.wrong_count) for item in analysis.errors_by_bloom] == [
        (1, 1),
        (2, 1),
        (3, 1),
    ]


def test_get_classroom_analysis_aggregates_students_tests_and_active_count(monkeypatch):
    level_one_question = _question(1, 1, "Questao 1", "Adicao")
    level_four_question = _question(2, 4, "Questao 2", "Geometria")
    classroom_test = _test(30, "Bimestral", "Misto", [level_one_question, level_four_question])

    student_a = SimpleNamespace(
        id=1,
        name="Maria",
        active=True,
        test_responses=[
            _response(30, classroom_test, 9.0, [2], date(2026, 3, 20)),
        ],
    )
    student_b = SimpleNamespace(
        id=2,
        name="Joao",
        active=False,
        test_responses=[
            _response(30, classroom_test, 6.0, [1], date(2026, 3, 21)),
            _response(30, classroom_test, None, [1, 2], date(2026, 3, 22)),
        ],
    )
    classroom = SimpleNamespace(
        id=5,
        name="Turma A",
        school_year=2026,
        grade_level="8 ano",
        shift="manha",
        students=[student_a, student_b],
    )

    monkeypatch.setattr(
        analysis_service,
        "_get_classroom_with_analysis_context",
        lambda _db, _classroom_id: classroom,
    )

    analysis = analysis_service.get_classroom_analysis(db=None, classroom_id=5)

    assert analysis.classroom_name == "Turma A"
    assert analysis.student_count == 2
    assert analysis.active_students == 1
    assert analysis.overall_average == 7.5
    assert [(item.test_id, item.average_score, item.attempts) for item in analysis.average_by_test] == [
        (30, 7.5, 2),
    ]
    assert [(item.student_id, item.average_score, item.attempts) for item in analysis.student_averages] == [
        (1, 9.0, 1),
        (2, 6.0, 2),
    ]
    assert [(item.content_name, item.wrong_count) for item in analysis.errors_by_content] == [
        ("Adicao", 2),
        ("Geometria", 2),
    ]
    assert [(item.level, item.wrong_count) for item in analysis.errors_by_bloom] == [
        (1, 2),
        (4, 2),
    ]


def test_generate_student_reinforcement_uses_latest_unique_wrong_questions(monkeypatch):
    question_one = _question(101, 2, "Questao sobre fracoes", "Fracoes")
    question_two = _question(202, 4, "Questao sobre area", "Geometria")
    first_test = _test(1, "Teste 1", "Operacoes", [question_one, question_two])
    second_test = _test(2, "Teste 2", "Geometria", [question_one])

    student = SimpleNamespace(
        id=9,
        name="Carlos",
        test_responses=[
            _response(1, first_test, 5.0, [1, 2], date(2026, 3, 20)),
            _response(2, second_test, 4.0, [1], date(2026, 3, 22)),
        ],
    )
    captured = {}
    created_payload = {}

    async def fake_generate(**kwargs):
        captured.update(kwargs)
        return {
            "questions": [
                {
                    "enunciation": "Qual fracao equivale a 1/2?",
                    "itens": ["1/4", "2/4", "3/4", "4/4"],
                    "correct_item": 1,
                    "level": 2,
                    "level_name": "Entender",
                    "contents": ["Fracoes"],
                },
                {
                    "enunciation": "Qual expressao calcula a area do retangulo?",
                    "itens": ["b + h", "2b + 2h", "b x h", "b / h"],
                    "correct_item": 2,
                    "level": 4,
                    "level_name": "Analisar",
                    "contents": ["Geometria"],
                },
            ]
        }

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def create_test(self, payload):
            created_payload["template"] = payload
            return SimpleNamespace(
                id=301,
                name=payload.name,
                kind="template",
                target_type="individual",
                created_by_user_id=payload.created_by_user_id,
            )

        def apply_test(self, template_id, payload, applied_by_user_id):
            created_payload["application"] = {
                "template_id": template_id,
                "payload": payload,
                "applied_by_user_id": applied_by_user_id,
            }
            return SimpleNamespace(
                id=401,
                name=payload.name,
                kind="application",
                target_type="individual",
            )

    monkeypatch.setattr(
        analysis_service,
        "_get_student_with_analysis_context",
        lambda _db, _student_id: student,
    )
    monkeypatch.setattr(analysis_service, "gerar_questoes_reforco", fake_generate)
    monkeypatch.setattr(analysis_service, "_persist_generated_questions", lambda _db, _questions: [11, 12])
    monkeypatch.setattr(analysis_service, "TestRepository", FakeTestRepository)

    reinforcement = asyncio.run(
        analysis_service.generate_student_reinforcement(db=None, student_id=9, current_user_id=77)
    )

    assert reinforcement.student_name == "Carlos"
    assert reinforcement.source_question_count == 2
    assert reinforcement.generated_question_count == 2
    assert reinforcement.created_template.id == 301
    assert reinforcement.created_application.id == 401
    assert reinforcement.pdf_download_url == "/test/applications/401/generate"
    assert reinforcement.generated_questions[0].level_name == "Entender"
    assert captured == {
        "questao_errada": ["Questao sobre fracoes", "Questao sobre area"],
        "nivel_bloom": [2, 4],
        "conteudo": ["Fracoes", "Geometria"],
        "incluir_todos_niveis": False,
    }
    assert created_payload["template"].questions == [11, 12]
    assert created_payload["template"].created_by_user_id == 77
    assert created_payload["application"]["template_id"] == 301
    assert created_payload["application"]["payload"].student_id == 9
    assert created_payload["application"]["applied_by_user_id"] == 77


def test_generate_student_reinforcement_requires_recorded_errors(monkeypatch):
    student = SimpleNamespace(
        id=9,
        name="Carlos",
        test_responses=[
            _response(1, _test(1, "Teste", "Tema", []), 10.0, [], date(2026, 3, 22)),
        ],
    )

    monkeypatch.setattr(
        analysis_service,
        "_get_student_with_analysis_context",
        lambda _db, _student_id: student,
    )

    with pytest.raises(ValidationError, match="nao possui erros|não possui erros"):
        asyncio.run(analysis_service.generate_student_reinforcement(db=None, student_id=9))


def test_generate_student_reinforcement_wraps_generation_failures(monkeypatch):
    question = _question(1, 3, "Resolva a equacao", "Equacao")
    student = SimpleNamespace(
        id=9,
        name="Carlos",
        test_responses=[
            _response(1, _test(1, "Teste", "Tema", [question]), 2.0, [1], date(2026, 3, 22)),
        ],
    )

    async def failing_generate(**_kwargs):
        raise RuntimeError("Groq indisponivel")

    monkeypatch.setattr(
        analysis_service,
        "_get_student_with_analysis_context",
        lambda _db, _student_id: student,
    )
    monkeypatch.setattr(analysis_service, "gerar_questoes_reforco", failing_generate)

    with pytest.raises(OperationError, match="Erro ao gerar reforco automatico|Erro ao gerar reforço automático"):
        asyncio.run(analysis_service.generate_student_reinforcement(db=None, student_id=9))
