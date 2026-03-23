from io import BytesIO
from sqlalchemy.orm import Session

from app.api.services.corretor import corrigir
from app.db.repositories.test_repository import TestRepository

def answer_sheet_corrector(image: BytesIO, test_id: int, db: Session):
    image.seek(0)

    repo = TestRepository(db)

    test = repo.get_test(test_id)

    gabarito = [question.correct_item for question in test.questions]

    resultado = corrigir(image, gabarito, len(gabarito), 5)

    return resultado
