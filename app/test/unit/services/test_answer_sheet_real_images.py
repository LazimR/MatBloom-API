from pathlib import Path
from types import SimpleNamespace

from app.api.services import answer_sheet_corrector
from app.api.services import corretor


SERVICE_DIR = Path(__file__).resolve().parents[3] / "api" / "services"
EXPONENTIATION_ANSWER_KEY = [0, 0, 1, 1, 4, 4, 4, 4, 4, 4]


def _load_image(name: str):
    return open(SERVICE_DIR / name, "rb")


def _build_application_test():
    return SimpleNamespace(
        kind="application",
        questions=[
            SimpleNamespace(correct_item=correct_item, itens=["A", "B", "C", "D", "E"])
            for correct_item in EXPONENTIATION_ANSWER_KEY
        ],
    )


def test_corrigir_reads_real_image_gabarito1_with_mocked_ocr(monkeypatch):
    monkeypatch.setattr(corretor.pt, "image_to_string", lambda *_args, **_kwargs: "ID: 1")

    with _load_image("gabarito1.jpg") as image_file:
        responses, score, student_id, wrong_questions = corretor.corrigir(
            image_file,
            EXPONENTIATION_ANSWER_KEY,
            10,
            5,
        )

    assert responses == [0, 0, 1, 1, 4, 4, 4, 4, 4, 4]
    assert score == 10
    assert student_id == "1"
    assert wrong_questions == []


def test_corrigir_reads_real_image_gabarito2_with_mocked_ocr(monkeypatch):
    monkeypatch.setattr(corretor.pt, "image_to_string", lambda *_args, **_kwargs: "ID: 1")

    with _load_image("gabarito2.jpg") as image_file:
        responses, score, student_id, wrong_questions = corretor.corrigir(
            image_file,
            EXPONENTIATION_ANSWER_KEY,
            10,
            5,
        )

    assert responses == [0, 0, 1, 1, 3, 0, 4, 4, 0, 0]
    assert score == 6
    assert student_id == "1"
    assert wrong_questions == [5, 6, 9, 10]


def test_answer_sheet_corrector_processes_real_image_with_application_fixture(monkeypatch):
    class FakeRepository:
        def __init__(self, _db):
            pass

        def get_test(self, _test_id):
            return _build_application_test()

    monkeypatch.setattr(corretor.pt, "image_to_string", lambda *_args, **_kwargs: "ID: 1")
    monkeypatch.setattr(answer_sheet_corrector, "TestRepository", FakeRepository)

    with _load_image("gabarito1.jpg") as image_file:
        result = answer_sheet_corrector.answer_sheet_corrector(image_file, test_id=2, db=None)

    assert result == [[0, 0, 1, 1, 4, 4, 4, 4, 4, 4], 10, "1", []]
