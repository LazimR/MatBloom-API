from io import BytesIO

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas.test_response import AnswerSheetConfirmation, TestResponseCreate, TestResponse
from app.api.security.auth import get_current_user_payload, ensure_test_scope, ensure_student_scope, require_academic_staff
from app.api.services.answer_sheet_corrector import answer_sheet_corrector as process_answer_sheet
from app.api.services.answer_sheet_upload import image_uploads
from app.core.academic import TestKind, TestTargetType
from app.core.exceptions import AppError, ConflictError, ValidationError
from app.db.models.connection import get_session
from app.db.models.models import Student, Test as TestModel, TestResponse as TestResponseModel
from app.db.repositories.test_repository import TestRepository
from app.db.repositories.test_response_repository import TestResponseRepository

router = APIRouter()


def _application(session, test_id, current_user, classroom_id=None, student_id=None):
    ensure_test_scope(test_id, session, current_user)
    test = TestRepository(session).get_test(test_id)
    if test.kind != TestKind.APPLICATION.value:
        raise ValidationError("Selecione uma aplicação de prova.")
    if not test.question_order_confirmed:
        raise ValidationError("Confirme a ordem original da aplicação antes de corrigir.")
    if classroom_id is not None and (test.target_type != TestTargetType.CLASS.value or test.classroom_id != classroom_id):
        raise ValidationError("A aplicação selecionada não pertence a esta turma.")
    if student_id is not None:
        ensure_student_scope(student_id, session, current_user)
        student = session.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise ValidationError("Aluno não encontrado.")
        if student.classroom_id != test.classroom_id or (test.target_type == TestTargetType.INDIVIDUAL.value and test.student_id != student_id):
            raise ValidationError("A aplicação selecionada não pertence a este aluno.")
    return test


@router.post("/preview")
def preview_answer_sheets(
    test_id: int,
    images: list[UploadFile] = File(...),
    classroom_id: int | None = None,
    student_id: int | None = None,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
    _authorized: dict = Depends(require_academic_staff),
):
    if (classroom_id is None) == (student_id is None):
        raise ValidationError("Informe uma turma ou um aluno para a correção.")
    test = _application(session, test_id, current_user, classroom_id, student_id)
    files = image_uploads(images, allow_zip=classroom_id is not None)
    results = []
    for name, content in files:
        try:
            answers, points, detected_id, wrong = process_answer_sheet(BytesIO(content), test_id, session)
            try:
                detected_id = int(detected_id)
            except (TypeError, ValueError):
                raise ValidationError("Não foi possível identificar o ID do aluno no gabarito.")
            if student_id is not None and detected_id != student_id:
                raise ValidationError("O ID lido na imagem não corresponde ao aluno selecionado.")
            ensure_student_scope(detected_id, session, current_user)
            student = session.query(Student).filter(Student.id == detected_id).first()
            if not student or student.classroom_id != test.classroom_id:
                raise ValidationError("O aluno identificado não pertence à turma da aplicação.")
            if test.target_type == TestTargetType.INDIVIDUAL.value and test.student_id != detected_id:
                raise ValidationError("O aluno identificado não é o aluno-alvo da aplicação.")
            attempts = session.query(TestResponseModel).filter(TestResponseModel.test_id == test_id, TestResponseModel.student_id == detected_id).count()
            results.append({"file": name, "student_id": detected_id, "student_name": student.name, "score": round(10 * points / len(test.questions), 2), "points": points, "total_questions": len(test.questions), "responses": answers, "wrong_questions": wrong, "existing_attempts": attempts})
        except AppError as exc:
            results.append({"file": name, "error": exc.detail})
        except HTTPException as exc:
            results.append({"file": name, "error": str(exc.detail)})
        except Exception:
            results.append({"file": name, "error": "Não foi possível processar esta imagem."})
    return {"test_id": test_id, "results": results}


@router.post("/confirm", response_model=TestResponse)
def confirm_answer_sheet(
    response: AnswerSheetConfirmation,
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
    _authorized: dict = Depends(require_academic_staff),
):
    test = _application(session, response.test_id, current_user, student_id=response.student_id)
    question_count = len(test.questions)
    if len(response.responses) != question_count:
        raise ValidationError("A quantidade de respostas não corresponde à prova.")
    for answer, question in zip(response.responses, test.questions):
        if answer < -1 or answer >= len(question.itens):
            raise ValidationError("A folha contém uma alternativa inválida.")
    wrong = [index for index, (answer, question) in enumerate(zip(response.responses, test.questions), start=1) if answer != question.correct_item]
    if response.counts_toward_average is not None:
        if response.expected_counts_toward_average is None:
            raise ValidationError("Informe a configuração atual da aplicação para evitar alterações simultâneas.")
        application = session.query(TestModel).filter(TestModel.id == response.test_id).populate_existing().with_for_update().first()
        if not application or application.counts_toward_average != response.expected_counts_toward_average:
            raise ConflictError("A configuração da média foi alterada. Atualize a página e confira novamente.")
        application.counts_toward_average = response.counts_toward_average
    validated = TestResponseCreate(**response.model_dump(exclude={"counts_toward_average", "expected_counts_toward_average"}, exclude_none=True))
    validated = validated.model_copy(update={"wrong_questions": wrong, "score": round(10 * (question_count - len(wrong)) / question_count, 2)})
    return TestResponseRepository(session).create_test_response(validated)


@router.post("/answer_sheet")
def submit_answer_sheet(
    test_id: int,
    image: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
    _authorized: dict = Depends(require_academic_staff),
):
    ensure_test_scope(test_id, session, current_user)
    result = process_answer_sheet(image.file, test_id, session)
    ensure_student_scope(int(result[2]), session, current_user)
    response = TestResponseCreate(test_id=test_id, student_id=int(result[2]), score=result[1], responses=result[0], wrong_questions=result[3])
    return TestResponseRepository(session).create_test_response(response)
