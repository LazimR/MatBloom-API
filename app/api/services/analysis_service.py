from collections import defaultdict
from statistics import mean

from sqlalchemy.orm import Session, joinedload

from app.api.schemas.analysis import (
    BloomErrorItem,
    BloomPerformanceItem,
    ClassroomAnalysis,
    ContentErrorItem,
    StudentAnalysis,
    StudentAverageItem,
    StudentReinforcement,
    TestAverageItem,
)
from app.api.services.system_analises import gerar_questoes_reforco
from app.core.exceptions import NotFoundError, OperationError, ValidationError
from app.db.models.models import Classroom, Question, Student, Test, TestResponse


BLOOM_LEVEL_NAMES = {
    1: "Lembrar",
    2: "Entender",
    3: "Aplicar",
    4: "Analisar",
    5: "Avaliar",
    6: "Criar",
}


def _round_score(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 2)


def _empty_bloom_stats() -> dict[int, dict[str, int]]:
    return {
        level: {
            "total_questions": 0,
            "correct_answers": 0,
            "wrong_answers": 0,
        }
        for level in BLOOM_LEVEL_NAMES
    }


def _build_bloom_performance(stats: dict[int, dict[str, int]]) -> list[BloomPerformanceItem]:
    return [
        BloomPerformanceItem(
            level=level,
            level_name=BLOOM_LEVEL_NAMES[level],
            total_questions=values["total_questions"],
            correct_answers=values["correct_answers"],
            wrong_answers=values["wrong_answers"],
            accuracy=_round_score(
                (values["correct_answers"] / values["total_questions"]) * 100
            )
            if values["total_questions"]
            else 0.0,
        )
        for level, values in stats.items()
    ]


def _build_error_by_bloom(stats: dict[int, dict[str, int]]) -> list[BloomErrorItem]:
    return [
        BloomErrorItem(
            level=level,
            level_name=BLOOM_LEVEL_NAMES[level],
            wrong_count=values["wrong_answers"],
        )
        for level, values in stats.items()
        if values["wrong_answers"] > 0
    ]


def _build_errors_by_content(content_errors: dict[str, int]) -> list[ContentErrorItem]:
    return [
        ContentErrorItem(content_name=content_name, wrong_count=wrong_count)
        for content_name, wrong_count in sorted(
            content_errors.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


def _build_average_by_test(aggregated_scores: dict[int, dict[str, object]]) -> list[TestAverageItem]:
    items: list[TestAverageItem] = []
    for test_id, values in aggregated_scores.items():
        scores = values["scores"]
        if not scores:
            continue
        items.append(
            TestAverageItem(
                test_id=test_id,
                test_name=str(values["name"]),
                average_score=_round_score(mean(scores)) or 0.0,
                attempts=len(scores),
            )
        )
    return sorted(items, key=lambda item: item.test_id)


def _accumulate_response_metrics(
    response: TestResponse,
    bloom_stats: dict[int, dict[str, int]],
    content_errors: dict[str, int],
):
    wrong_positions = set(response.wrong_questions or [])
    test_questions = response.test.questions if response.test else []

    for index, question in enumerate(test_questions, start=1):
        stats = bloom_stats.setdefault(
            question.level,
            {"total_questions": 0, "correct_answers": 0, "wrong_answers": 0},
        )
        stats["total_questions"] += 1

        if index in wrong_positions:
            stats["wrong_answers"] += 1
            for content in question.contents:
                content_errors[content.name] += 1
        else:
            stats["correct_answers"] += 1


def _get_student_with_analysis_context(db: Session, student_id: int) -> Student:
    student = (
        db.query(Student)
        .options(
            joinedload(Student.classroom),
            joinedload(Student.test_responses)
            .joinedload(TestResponse.test)
            .joinedload(Test.questions)
            .joinedload(Question.contents),
        )
        .filter(Student.id == student_id)
        .first()
    )
    if not student:
        raise NotFoundError(f"Student with ID {student_id} does not exist.")
    return student


def _get_classroom_with_analysis_context(db: Session, classroom_id: int) -> Classroom:
    classroom = (
        db.query(Classroom)
        .options(
            joinedload(Classroom.students)
            .joinedload(Student.test_responses)
            .joinedload(TestResponse.test)
            .joinedload(Test.questions)
            .joinedload(Question.contents),
        )
        .filter(Classroom.id == classroom_id)
        .first()
    )
    if not classroom:
        raise NotFoundError(f"Classroom with ID {classroom_id} does not exist.")
    return classroom


def get_student_analysis(db: Session, student_id: int) -> StudentAnalysis:
    student = _get_student_with_analysis_context(db, student_id)

    scores = [response.score for response in student.test_responses if response.score is not None]
    average_by_test: dict[int, dict[str, object]] = defaultdict(lambda: {"name": "", "scores": []})
    bloom_stats = _empty_bloom_stats()
    content_errors: dict[str, int] = defaultdict(int)

    for response in student.test_responses:
        if response.test is None:
            continue
        average_by_test[response.test_id]["name"] = response.test.name
        if response.score is not None:
            average_by_test[response.test_id]["scores"].append(response.score)
        _accumulate_response_metrics(response, bloom_stats, content_errors)

    return StudentAnalysis(
        student_id=student.id,
        student_name=student.name,
        classroom_id=student.classroom_id,
        overall_average=_round_score(mean(scores)) if scores else None,
        total_attempts=len(student.test_responses),
        average_by_test=_build_average_by_test(average_by_test),
        bloom_performance=_build_bloom_performance(bloom_stats),
        errors_by_content=_build_errors_by_content(content_errors),
        errors_by_bloom=_build_error_by_bloom(bloom_stats),
    )


def get_classroom_analysis(db: Session, classroom_id: int) -> ClassroomAnalysis:
    classroom = _get_classroom_with_analysis_context(db, classroom_id)

    all_scores: list[float] = []
    average_by_test: dict[int, dict[str, object]] = defaultdict(lambda: {"name": "", "scores": []})
    bloom_stats = _empty_bloom_stats()
    content_errors: dict[str, int] = defaultdict(int)
    student_averages: list[StudentAverageItem] = []

    for student in classroom.students:
        student_scores = [response.score for response in student.test_responses if response.score is not None]
        all_scores.extend(student_scores)

        for response in student.test_responses:
            if response.test is None:
                continue
            average_by_test[response.test_id]["name"] = response.test.name
            if response.score is not None:
                average_by_test[response.test_id]["scores"].append(response.score)
            _accumulate_response_metrics(response, bloom_stats, content_errors)

        student_averages.append(
            StudentAverageItem(
                student_id=student.id,
                student_name=student.name,
                average_score=_round_score(mean(student_scores)) if student_scores else None,
                attempts=len(student.test_responses),
            )
        )

    return ClassroomAnalysis(
        classroom_id=classroom.id,
        classroom_name=classroom.name,
        school_year=classroom.school_year,
        grade_level=classroom.grade_level,
        shift=classroom.shift,
        student_count=len(classroom.students),
        active_students=sum(1 for student in classroom.students if student.active),
        overall_average=_round_score(mean(all_scores)) if all_scores else None,
        average_by_test=_build_average_by_test(average_by_test),
        bloom_performance=_build_bloom_performance(bloom_stats),
        errors_by_content=_build_errors_by_content(content_errors),
        errors_by_bloom=_build_error_by_bloom(bloom_stats),
        student_averages=sorted(student_averages, key=lambda item: item.student_id),
    )


async def generate_student_reinforcement(db: Session, student_id: int) -> StudentReinforcement:
    student = _get_student_with_analysis_context(db, student_id)

    wrong_questions_payload: dict[int, tuple[str, int, str]] = {}

    sorted_responses = sorted(
        student.test_responses,
        key=lambda response: response.attempt_date,
        reverse=True,
    )

    for response in sorted_responses:
        if response.test is None:
            continue
        wrong_positions = set(response.wrong_questions or [])
        for index, question in enumerate(response.test.questions, start=1):
            if index not in wrong_positions:
                continue
            if question.id in wrong_questions_payload:
                continue
            content_name = question.contents[0].name if question.contents else response.test.theme
            wrong_questions_payload[question.id] = (
                question.enunciation,
                question.level,
                content_name,
            )

    if not wrong_questions_payload:
        raise ValidationError("O aluno ainda não possui erros registrados para gerar reforço.")

    try:
        reinforcement = await gerar_questoes_reforco(
            questao_errada=[item[0] for item in wrong_questions_payload.values()],
            nivel_bloom=[item[1] for item in wrong_questions_payload.values()],
            conteudo=[item[2] for item in wrong_questions_payload.values()],
            incluir_todos_niveis=False,
        )
    except Exception as exc:
        raise OperationError(f"Erro ao gerar reforço automático: {exc}") from exc

    return StudentReinforcement(
        student_id=student.id,
        student_name=student.name,
        source_question_count=len(wrong_questions_payload),
        generated_reinforcement=reinforcement,
    )
