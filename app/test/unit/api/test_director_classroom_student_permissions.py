from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from app.api.endpoints import classroom as classroom_endpoint, student as student_endpoint
from app.api.security import auth
from app.db.models.connection import get_session
from app.main import app


class ClassroomRepositoryStub:
    def __init__(self, _db):
        pass
    def create_classroom(self, data):
        return {"id": 2, **data.model_dump(), "teachers": [], "students": []}
    def update_classroom(self, data):
        return {"id": data.id, "name": data.name, "school_year": 2026, "grade_level": "9º ano", "shift": "manha", "active": True, "teachers": [], "students": []}


class StudentRepositoryStub:
    def __init__(self, _db):
        pass
    def create_student(self, data):
        return {"id": 3, **data.model_dump(), "created_at": datetime(2026, 1, 1), "test_responses": []}
    def update_student(self, data):
        return {"id": data.id, "name": data.name, "registration": "001", "classroom_id": 2, "active": True, "created_at": datetime(2026, 1, 1), "test_responses": []}


@pytest.mark.parametrize("role,status", [("diretor", 200), ("admin", 200), ("professor", 403)])
@pytest.mark.parametrize("method,path,body", [
    ("post", "/classroom/", {"name": "Turma", "school_year": 2026, "grade_level": "9º ano", "shift": "manha"}),
    ("put", "/classroom/", {"id": 2, "name": "Turma atualizada"}),
    ("post", "/student/", {"name": "Aluno", "registration": "001", "classroom_id": 2}),
    ("put", "/student/", {"id": 3, "name": "Aluno atualizado"}),
])
def test_classroom_and_student_management_permissions(monkeypatch, role, status, method, path, body):
    app.dependency_overrides.clear()
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": role, "user_id": 1}
    app.dependency_overrides[get_session] = lambda: None
    monkeypatch.setattr(classroom_endpoint, "ClassroomRepository", ClassroomRepositoryStub)
    monkeypatch.setattr(student_endpoint, "StudentRepository", StudentRepositoryStub)
    with TestClient(app) as client:
        response = client.request(method, path, json=body)
    assert response.status_code == status
    app.dependency_overrides.clear()
