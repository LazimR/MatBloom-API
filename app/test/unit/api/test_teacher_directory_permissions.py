import pytest
from fastapi.testclient import TestClient

from app.api.endpoints import user as user_endpoint
from app.api.security import auth
from app.db.models.connection import get_session
from app.main import app


class RepositoryStub:
    def __init__(self, _db):
        pass

    def list_teachers(self):
        return [{"id": 7, "username": "professor", "email": "prof@example.com", "password": "não deve aparecer", "role": "professor"}]

    def add_classroom_to_user(self, user_id, classroom_id):
        return {"id": user_id, "username": "professor", "email": "prof@example.com", "role": "professor", "classes": []}

    def remove_classroom_from_user(self, user_id, classroom_id):
        return {"id": user_id, "username": "professor", "email": "prof@example.com", "role": "professor", "classes": []}


@pytest.mark.parametrize("role,allowed", [("admin", True), ("diretor", True), ("professor", False)])
@pytest.mark.parametrize("method,path", [
    ("get", "/user/directory/teachers"),
    ("post", "/user/7/classrooms/2"),
    ("delete", "/user/7/classrooms/2"),
])
def test_teacher_directory_and_links_are_restricted(monkeypatch, role, allowed, method, path):
    app.dependency_overrides.clear()
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": role, "user_id": 1}
    app.dependency_overrides[get_session] = lambda: None
    monkeypatch.setattr(user_endpoint, "UserRepository", RepositoryStub)
    try:
        with TestClient(app) as client:
            response = client.request(method, path)
        assert response.status_code == (200 if allowed else 403)
        if allowed and method == "get":
            assert response.json() == [{"id": 7, "username": "professor", "email": "prof@example.com"}]
    finally:
        app.dependency_overrides.clear()
