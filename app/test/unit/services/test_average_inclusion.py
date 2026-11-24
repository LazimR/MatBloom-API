from types import SimpleNamespace as NS

from app.api.services import analysis_service


def test_reinforcement_scores_do_not_change_averages_but_keep_diagnostics(monkeypatch):
    question = NS(id=1, level=3, contents=[NS(name="Frações")])
    counted = NS(name="Avaliação", questions=[question], counts_toward_average=True, question_order_confirmed=True)
    practice = NS(name="Reforço", questions=[question], counts_toward_average=False, question_order_confirmed=True)
    student = NS(id=1, name="Ana", classroom_id=3, active=True, test_responses=[
        NS(test=counted, test_id=1, score=8, wrong_questions=[]),
        NS(test=practice, test_id=2, score=2, wrong_questions=[1]),
    ])
    classroom = NS(id=3, name="Turma", school_year=2026, grade_level="9", shift="manha", students=[student])
    monkeypatch.setattr(analysis_service, "_get_student_with_analysis_context", lambda *_: student)
    monkeypatch.setattr(analysis_service, "_get_classroom_with_analysis_context", lambda *_: classroom)

    pupil = analysis_service.get_student_analysis(None, 1)
    group = analysis_service.get_classroom_analysis(None, 3)
    assert pupil.overall_average == 8
    assert group.overall_average == 8
    assert group.student_averages[0].average_score == 8
    assert pupil.total_attempts == 2
    assert [(entry.test_id, entry.average_score) for entry in pupil.average_by_test] == [(1, 8), (2, 2)]
    assert [(entry.content_name, entry.wrong_count) for entry in pupil.errors_by_content] == [("Frações", 1)]
    assert pupil.bloom_performance[2].total_questions == 2
    assert group.errors_by_content[0].wrong_count == 1


def test_only_reinforcement_leaves_average_unavailable(monkeypatch):
    practice = NS(name="Reforço", questions=[], counts_toward_average=False, question_order_confirmed=True)
    student = NS(id=1, name="Ana", classroom_id=3, active=True, test_responses=[NS(test=practice, test_id=2, score=5, wrong_questions=[])])
    monkeypatch.setattr(analysis_service, "_get_student_with_analysis_context", lambda *_: student)
    assert analysis_service.get_student_analysis(None, 1).overall_average is None
