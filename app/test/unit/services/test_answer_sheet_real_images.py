from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from app.api.services import answer_sheet_corrector, corretor
from app.core.exceptions import ValidationError

SERVICE_DIR = Path(__file__).resolve().parents[3] / "api" / "services"
ANSWER_KEY = [0, 1, 2, 3, 0]


def _load_image(name: str):
    return open(SERVICE_DIR / name, "rb")


def _build_application_test():
    return SimpleNamespace(
        kind="application",
        questions=[SimpleNamespace(correct_item=item, itens=["A", "B", "C", "D"]) for item in ANSWER_KEY],
    )


@pytest.mark.parametrize("name,expected,points,wrong", [
    ("gabarito_vazio.jpg", [-1, -1, -1, -1, -1], 0, [1, 2, 3, 4, 5]),
    ("gabarito1.jpg", [0, 1, 3, 3, 2], 3, [3, 5]),
    ("gabarito2.jpg", [0, 1, 2, 3, 0], 5, []),
])
def test_corrigir_reads_real_answer_sheets(monkeypatch, name, expected, points, wrong):
    monkeypatch.setattr(corretor.pt, "image_to_string", lambda *_args, **_kwargs: "ID: 1")
    with _load_image(name) as image_file:
        result = corretor.corrigir(image_file, ANSWER_KEY, 5, 4)
    assert result == [expected, points, "1", wrong]


@pytest.mark.parametrize("questions,alternatives", [(5, 5), (10, 4), (10, 5)])
def test_rejects_real_answer_sheet_with_wrong_format(monkeypatch, questions, alternatives):
    monkeypatch.setattr(corretor.pt, "image_to_string", lambda *_args, **_kwargs: "ID: 1")
    with _load_image("gabarito_vazio.jpg") as image_file:
        with pytest.raises(ValidationError, match="gabarito parece ter"):
            corretor.corrigir(image_file, [0] * questions, questions, alternatives)


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
    assert result == [[0, 1, 3, 3, 2], 3, "1", [3, 5]]


@pytest.mark.parametrize("questions,alternatives", [(5, 4), (5, 5), (10, 5), (3, 2)])
def test_grid_format_validation_accepts_matching_sheets(questions, alternatives):
    image = np.zeros((questions * 120, alternatives * 120), dtype=np.uint8)
    for row in range(questions):
        for column in range(alternatives):
            cv2.circle(image, (column * 120 + 60, row * 120 + 60), 22, 255, -1 if column == row % alternatives else 3)
    corretor.validar_formato_gabarito(image, questions, alternatives)
