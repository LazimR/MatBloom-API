from io import BytesIO
from PIL import Image

from app.api.services.corretor import corrigir
from app.db.repositories.test_repository import TestRepository
from app.db.models.connection import get_session

def answer_sheet_corrector(image: BytesIO, test_id: int):
    session = get_session()

    repo = TestRepository(session)

    test = repo.get_test(test_id)

    gabarito = [correct_item for question in test.questions 
                for correct_item in question.correct_item]

    img = Image.open(image)

    resultado = corrigir(img, gabarito, len(gabarito), 5)

    return resultado