from io import BytesIO
from zipfile import ZipFile
from app.api.services.pdf_generate import pdf_test_generate, generate_answer_sheet
from app.db.repositories.test_repository import TestRepository
from app.db.models.connection import get_session

def test_generate(test_id: int , student_names: list[str], student_ids: list[str], db):    
    rep = TestRepository(db)

    test = rep.get_test(test_id)

    pdf_buffers = []

    questions = [question.dict() for question in test.questions]

    for i, student_name in enumerate(student_names):
        student_id = student_ids[i] if student_ids else None

        pdf_buffer = pdf_test_generate(test.name, questions, student_name, student_id)
        pdf_buffers.append((f"{student_name}_teste.pdf", pdf_buffer))

        answer_sheet_buffer = generate_answer_sheet(student_name, student_id, len(questions), len(questions[0]['itens']))
        pdf_buffers.append((f"{student_name}_gabarito.pdf", answer_sheet_buffer))


    # Cria um arquivo ZIP em memória
    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, "w") as zip_file:
        for filename, pdf_buffer in pdf_buffers:
            zip_file.writestr(filename, pdf_buffer.getvalue())

    zip_buffer.seek(0)

    # Retorna o arquivo ZIP como resposta
    return zip_buffer

