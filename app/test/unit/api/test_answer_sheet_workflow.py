from io import BytesIO
from types import SimpleNamespace
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from fastapi.testclient import TestClient

from app.api.endpoints import answer_sheet as endpoint
from app.api.security import auth
from app.api.services.answer_sheet_upload import image_uploads
from app.core.exceptions import ValidationError
from app.db.models.connection import get_session
from app.db.models.models import Student, Test as ExamModel
from app.main import app


class FakeQuery:
    def __init__(self, student=None):
        self.student = student
    def filter(self, *_args):
        return self
    def populate_existing(self):
        return self
    def with_for_update(self):
        return self
    def first(self):
        return self.student
    def count(self):
        return 0


class FakeSession:
    def __init__(self):
        self.application = SimpleNamespace(counts_toward_average=True)
    def query(self, model):
        if model is ExamModel:
            return FakeQuery(self.application)
        if model is Student:
            return FakeQuery(SimpleNamespace(id=7, name="Ana", classroom_id=2))
        return FakeQuery()


@pytest.fixture
def client(monkeypatch):
    import cv2
    cv2.setNumThreads(1)
    app.dependency_overrides.clear()
    app.dependency_overrides[auth.require_academic_staff] = lambda: {"role": "professor", "user_id": 3}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 3}
    db = FakeSession()
    app.dependency_overrides[get_session] = lambda: db
    monkeypatch.setattr(endpoint, "ensure_test_scope", lambda *_args: None)
    monkeypatch.setattr(endpoint, "ensure_student_scope", lambda *_args: None)
    questions = [SimpleNamespace(correct_item=0, itens=["a", "b"]), SimpleNamespace(correct_item=1, itens=["a", "b"]), SimpleNamespace(correct_item=0, itens=["a", "b"])]
    test = SimpleNamespace(kind="application", question_order_confirmed=True, classroom_id=2, target_type="turma", student_id=None, questions=questions)
    monkeypatch.setattr(endpoint, "TestRepository", lambda _db: SimpleNamespace(get_test=lambda _id: test))
    with TestClient(app) as http:
        yield http
    app.dependency_overrides.clear()


def test_preview_classroom_zip_reports_each_image_without_saving(client, monkeypatch):
    def correct(file, _test_id, _session):
        if file.read() == b"bad":
            raise ValidationError("Imagem ilegível.")
        return [[0, 1, -1], 2, "7", [3]]
    monkeypatch.setattr(endpoint, "process_answer_sheet", correct)
    monkeypatch.setattr(endpoint, "TestResponseRepository", lambda _db: pytest.fail("Prévia não deve gravar dados"))
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as file:
        file.writestr("subdir/ok.png", b"good")
        file.writestr("bad.jpg", b"bad")
    response = client.post("/answer-sheet/preview?test_id=1&classroom_id=2", files={"images": ("lote.zip", archive.getvalue(), "application/zip")})
    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0]["student_id"] == 7
    assert results[0]["score"] == 6.67
    assert results[0]["responses"] == [0, 1, -1]
    assert results[1]["error"] == "Imagem ilegível."


def test_student_preview_rejects_wrong_detected_student(client, monkeypatch):
    monkeypatch.setattr(endpoint, "process_answer_sheet", lambda *_args: [[0, 1, 0], 3, "8", []])
    response = client.post("/answer-sheet/preview?test_id=1&student_id=7", files={"images": ("sheet.png", b"image", "image/png")})
    assert response.status_code == 200
    assert "não corresponde" in response.json()["results"][0]["error"]


def test_preview_rejects_application_from_other_classroom(client):
    response = client.post("/answer-sheet/preview?test_id=1&classroom_id=3", files={"images": ("sheet.png", b"image", "image/png")})
    assert response.status_code == 400


def test_confirm_recalculates_score_and_wrong_answers(client, monkeypatch):
    def save(data):
        return {"id": 99, **data.model_dump()}
    monkeypatch.setattr(endpoint, "TestResponseRepository", lambda _db: SimpleNamespace(create_test_response=save))
    response = client.post("/answer-sheet/confirm", json={"test_id": 1, "student_id": 7, "score": 10, "responses": [0, 1, -1], "wrong_questions": []})
    assert response.status_code == 200
    assert response.json()["score"] == 6.67
    assert response.json()["wrong_questions"] == [3]


@pytest.mark.parametrize("answers,score,wrong", [
    ([0, 1, 0], 10, []),
    ([1, -1, 0], 3.33, [1, 2]),
])
def test_confirm_saves_edited_answers_and_recalculates(client, monkeypatch, answers, score, wrong):
    monkeypatch.setattr(endpoint, "TestResponseRepository", lambda _db: SimpleNamespace(create_test_response=lambda data: {"id": 99, **data.model_dump()}))
    response = client.post("/answer-sheet/confirm", json={"test_id": 1, "student_id": 7, "score": 0, "responses": answers, "wrong_questions": []})
    assert response.status_code == 200
    assert response.json()["responses"] == answers
    assert response.json()["score"] == score
    assert response.json()["wrong_questions"] == wrong


def test_confirm_rejects_invalid_edited_answer(client, monkeypatch):
    monkeypatch.setattr(endpoint, "TestResponseRepository", lambda _db: pytest.fail("Não deve gravar dados"))
    response = client.post("/answer-sheet/confirm", json={"test_id": 1, "student_id": 7, "score": 0, "responses": [0, 2, -1], "wrong_questions": []})
    assert response.status_code == 400


def test_student_cannot_upload_zip():
    upload = SimpleNamespace(filename="lote.zip", file=BytesIO(b"not-a-zip"))
    with pytest.raises(ValidationError, match="única imagem"):
        image_uploads([upload], allow_zip=False)


def test_zip_rejects_non_image_file():
    archive = BytesIO()
    with ZipFile(archive, "w") as file:
        file.writestr("not-image.txt", "no")
    upload = SimpleNamespace(filename="lote.zip", file=BytesIO(archive.getvalue()))
    with pytest.raises(ValidationError, match="não é imagem"):
        image_uploads([upload], allow_zip=True)


def test_preview_processes_real_image_through_ocr_pipeline(client, monkeypatch):
    from pathlib import Path
    from app.api.services import answer_sheet_corrector, corretor

    key = [0, 1, 2, 3, 0]
    questions = [SimpleNamespace(correct_item=answer, itens=["A", "B", "C", "D"]) for answer in key]
    test = SimpleNamespace(kind="application", question_order_confirmed=True, classroom_id=2, target_type="turma", student_id=None, questions=questions)
    monkeypatch.setattr(endpoint, "TestRepository", lambda _db: SimpleNamespace(get_test=lambda _id: test))
    monkeypatch.setattr(answer_sheet_corrector, "TestRepository", lambda _db: SimpleNamespace(get_test=lambda _id: test))
    monkeypatch.setattr(corretor.pt, "image_to_string", lambda *_args, **_kwargs: "ID: 7")
    image = Path("app/api/services/gabarito1.jpg").read_bytes()
    response = client.post("/answer-sheet/preview?test_id=1&student_id=7", files={"images": ("gabarito.jpg", image, "image/jpeg")})
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["student_id"] == 7
    assert result["responses"] == [0, 1, 3, 3, 2]
    assert result["score"] == 6
    assert result["wrong_questions"] == [3, 5]


def test_confirm_updates_application_inclusion_and_recomputes_score(client, monkeypatch):
    db = app.dependency_overrides[get_session]()
    monkeypatch.setattr(endpoint, "TestResponseRepository", lambda _db: SimpleNamespace(create_test_response=lambda data: {"id": 99, **data.model_dump()}))
    response = client.post("/answer-sheet/confirm", json={"test_id": 1, "student_id": 7, "score": 10, "responses": [0, 1, -1], "wrong_questions": [], "counts_toward_average": False, "expected_counts_toward_average": True})
    assert response.status_code == 200
    assert db.application.counts_toward_average is False
    assert response.json()["score"] == 6.67


def test_confirm_rejects_stale_average_setting_without_saving(client, monkeypatch):
    db = app.dependency_overrides[get_session]()
    db.application.counts_toward_average = False
    monkeypatch.setattr(endpoint, "TestResponseRepository", lambda _db: pytest.fail("Não deve gravar dados"))
    response = client.post("/answer-sheet/confirm", json={"test_id": 1, "student_id": 7, "score": 10, "responses": [0, 1, 0], "wrong_questions": [], "counts_toward_average": True, "expected_counts_toward_average": True})
    assert response.status_code == 409
    assert db.application.counts_toward_average is False
