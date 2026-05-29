from io import BytesIO
from sqlalchemy.orm import Session

from app.api.services.corretor import corrigir
from app.core.academic import TestKind
from app.core.exceptions import OperationError, ValidationError
from app.db.repositories.test_repository import TestRepository


def answer_sheet_corrector(image: BytesIO, test_id: int, db: Session):
    image.seek(0)

    repo = TestRepository(db)

    test = repo.get_test(test_id)
    if test.kind != TestKind.APPLICATION.value:
        raise ValidationError("A correção automática só pode ser feita para uma aplicação de prova.")

    gabarito = [question.correct_item for question in test.questions]
    if any(item is None for item in gabarito):
        raise ValidationError("A prova aplicada possui questões sem alternativa correta definida.")

    numero_alternativas = len(test.questions[0].itens) if test.questions else 0
    if numero_alternativas <= 0:
        raise ValidationError("A prova aplicada não possui alternativas válidas para correção.")

    try:
        resultado = corrigir(image, gabarito, len(gabarito), numero_alternativas)
    except ValidationError:
        raise
    except Exception as exc:
        raise OperationError(f"Erro ao executar a correção da folha de respostas: {exc}") from exc

    if not resultado:
        raise OperationError("A correção da folha de respostas não retornou resultado.")
    if resultado[2] is None:
        raise ValidationError("Não foi possível identificar o ID do aluno no gabarito.")

    return resultado
