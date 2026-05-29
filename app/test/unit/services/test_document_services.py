from io import BytesIO
from types import SimpleNamespace

import pytest

from app.api.services import answer_sheet_corrector, corretor, pdf_generate
from app.core.exceptions import OperationError, ValidationError


def test_pdf_test_generate_requires_questions():
    with pytest.raises(ValidationError, match="pelo menos uma questão"):
        pdf_generate.pdf_test_generate("Prova 1", [], "Maria", "7")


def test_generate_answer_sheet_requires_student_id():
    with pytest.raises(ValidationError, match="ID do aluno"):
        pdf_generate.generate_answer_sheet("Maria", "", 10, 5)


def test_generate_answer_sheet_supports_dynamic_question_count():
    pdf_buffer = pdf_generate.generate_answer_sheet("Maria", "7", 16, 4)

    assert pdf_buffer.getvalue()


def test_pdf_test_generate_wraps_unexpected_errors(monkeypatch):
    monkeypatch.setattr(pdf_generate, "_ensure_pdf_fonts_registered", lambda: None)

    class FakeDoc:
        def __init__(self, *_args, **_kwargs):
            pass

        def build(self, _story):
            raise RuntimeError("falha reportlab")

    monkeypatch.setattr(pdf_generate, "SimpleDocTemplate", FakeDoc)

    with pytest.raises(OperationError, match="Erro ao gerar PDF da prova"):
        pdf_generate.pdf_test_generate(
            "Prova 1",
            [{"enunciation": "Quanto e 2 + 2?", "itens": ["1", "2", "3"]}],
            "Maria",
            "7",
        )


def test_corrigir_rejects_invalid_image():
    with pytest.raises(ValidationError, match="não pôde ser carregada|nao pôde ser carregada"):
        corretor.corrigir(BytesIO(b"not-an-image"), [0, 1], 2, 5)


def test_answer_sheet_corrector_requires_test_application(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return SimpleNamespace(
                kind="template",
                questions=[
                    SimpleNamespace(correct_item=0, itens=["A", "B", "C"]),
                ],
            )

    monkeypatch.setattr(answer_sheet_corrector, "TestRepository", FakeRepository)

    with pytest.raises(ValidationError, match="aplicação de prova"):
        answer_sheet_corrector.answer_sheet_corrector(BytesIO(b"image"), 1, db=None)


def test_answer_sheet_corrector_wraps_unexpected_correction_errors(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return SimpleNamespace(
                kind="application",
                questions=[
                    SimpleNamespace(correct_item=0, itens=["A", "B", "C"]),
                ],
            )

    def failing_corrigir(*_args, **_kwargs):
        raise RuntimeError("opencv falhou")

    monkeypatch.setattr(answer_sheet_corrector, "TestRepository", FakeRepository)
    monkeypatch.setattr(answer_sheet_corrector, "corrigir", failing_corrigir)

    with pytest.raises(OperationError, match="Erro ao executar a correção"):
        answer_sheet_corrector.answer_sheet_corrector(BytesIO(b"image"), 1, db=None)


def test_answer_sheet_corrector_requires_detected_student_id(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return SimpleNamespace(
                kind="application",
                questions=[
                    SimpleNamespace(correct_item=0, itens=["A", "B", "C"]),
                ],
            )

    monkeypatch.setattr(answer_sheet_corrector, "TestRepository", FakeRepository)
    monkeypatch.setattr(answer_sheet_corrector, "corrigir", lambda *_args, **_kwargs: [[0], 1, None, []])

    with pytest.raises(ValidationError, match="identificar o ID do aluno"):
        answer_sheet_corrector.answer_sheet_corrector(BytesIO(b"image"), 1, db=None)
