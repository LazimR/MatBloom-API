from datetime import date, datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.endpoints import classroom as classroom_endpoint
from app.api.endpoints import student as student_endpoint
from app.api.endpoints import test as test_endpoint
from app.api.endpoints import test_response as test_response_endpoint
from app.api.endpoints import user as user_endpoint
from app.api.schemas.analysis import ClassroomAnalysis, StudentAnalysis
from app.api.schemas.user import User as UserSchema
from app.api.security import auth
from app.main import app


@pytest.fixture
def client():
    app.dependency_overrides.clear()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_read_root(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to MatBloom API!"}


def test_create_first_user_without_auth(client, monkeypatch):
    class FakeUserRepository:
        def __init__(self, _db):
            pass

        def has_any_user(self):
            return False

        def create_user(self, user):
            return {
                "id": 1,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "classes": [],
            }

    monkeypatch.setattr(user_endpoint, "UserRepository", FakeUserRepository)

    response = client.post(
        "/user/",
        json={
            "username": "admin",
            "email": "admin@matbloom.com",
            "password": "123456",
            "role": "admin",
        },
    )

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert "password" not in response.json()


def test_create_user_requires_admin_after_bootstrap(client, monkeypatch):
    class FakeUserRepository:
        def __init__(self, _db):
            pass

        def has_any_user(self):
            return True

    monkeypatch.setattr(user_endpoint, "UserRepository", FakeUserRepository)

    response = client.post(
        "/user/",
        json={
            "username": "teacher",
            "email": "teacher@matbloom.com",
            "password": "123456",
            "role": "professor",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Apenas administradores podem criar usuários."


def test_login_sets_http_only_cookie_and_returns_session_user(client, monkeypatch):
    fake_user = UserSchema.model_validate(
        {
            "id": 7,
            "username": "professor",
            "email": "professor@matbloom.com",
            "role": "professor",
            "classes": [],
        }
    )

    class FakeUserRepository:
        def __init__(self, _db):
            pass

        def authenticate_user(self, _user):
            return fake_user

    monkeypatch.setattr(user_endpoint, "UserRepository", FakeUserRepository)

    response = client.post(
        "/user/login",
        data={"username": "professor", "password": "123456"},
    )

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "user": fake_user.model_dump(mode="json")}
    assert "matbloom_access_token=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


def test_session_reads_authenticated_user_from_cookie(client, monkeypatch):
    fake_user = UserSchema.model_validate(
        {
            "id": 7,
            "username": "professor",
            "email": "professor@matbloom.com",
            "role": "professor",
            "classes": [],
        }
    )

    class FakeUserRepository:
        def __init__(self, _db):
            pass

        def authenticate_user(self, _user):
            return fake_user

        def get_user_by_username(self, username):
            assert username == "professor"
            return fake_user

    monkeypatch.setattr(user_endpoint, "UserRepository", FakeUserRepository)

    login_response = client.post(
        "/user/login",
        data={"username": "professor", "password": "123456"},
    )

    response = client.get("/user/session", cookies=login_response.cookies)

    assert response.status_code == 200
    assert response.json() == {"authenticated": True, "user": fake_user.model_dump(mode="json")}


def test_logout_clears_auth_cookie(client):
    response = client.post("/user/logout")

    assert response.status_code == 200
    assert response.json() == {"detail": "Sessão encerrada com sucesso."}
    assert "matbloom_access_token=\"\"" in response.headers["set-cookie"]


def test_create_classroom_requires_director_or_admin(client, monkeypatch):
    app.dependency_overrides[auth.require_director_or_admin] = lambda: {"role": "diretor"}

    class FakeClassroomRepository:
        def __init__(self, _db):
            pass

        def create_classroom(self, classroom):
            return {
                "id": 10,
                "name": classroom.name,
                "school_year": classroom.school_year,
                "grade_level": classroom.grade_level,
                "shift": classroom.shift.value,
                "active": classroom.active,
                "teacher_ids": [],
                "teachers": [],
                "students": [],
            }

    monkeypatch.setattr(classroom_endpoint, "ClassroomRepository", FakeClassroomRepository)

    response = client.post(
        "/classroom/",
        json={
            "name": "Turma A",
            "school_year": 2026,
            "grade_level": "8 ano",
            "shift": "matutino_vespertino",
            "active": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["shift"] == "matutino_vespertino"


def test_director_can_list_all_classrooms_with_teacher_ids(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "diretor", "user_id": 5}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "diretor", "user_id": 5}

    class FakeClassroomRepository:
        def __init__(self, _db):
            pass

        def list_classrooms(self, classroom_ids=None):
            assert classroom_ids is None
            return [
                {
                    "id": 1,
                    "name": "Turma Exponenciação A",
                    "school_year": 2026,
                    "grade_level": "9 ano",
                    "shift": "manha",
                    "active": True,
                    "teacher_ids": [2],
                    "teachers": [
                        {
                            "id": 2,
                            "username": "prof_expo",
                            "email": "prof.expo@matbloom.com",
                        }
                    ],
                    "students": [],
                }
            ]

    monkeypatch.setattr(classroom_endpoint, "ClassroomRepository", FakeClassroomRepository)

    response = client.get("/classroom/")

    assert response.status_code == 200
    assert response.json()[0]["teacher_ids"] == [2]
    assert response.json()[0]["teachers"][0]["username"] == "prof_expo"


def test_create_student_requires_director_or_admin(client, monkeypatch):
    app.dependency_overrides[auth.require_director_or_admin] = lambda: {"role": "diretor"}

    class FakeStudentRepository:
        def __init__(self, _db):
            pass

        def create_student(self, student):
            return {
                "id": 7,
                "name": student.name,
                "registration": student.registration,
                "classroom_id": student.classroom_id,
                "active": student.active,
                "created_at": datetime(2026, 3, 23, 10, 0, 0),
                "test_responses": [],
            }

    monkeypatch.setattr(student_endpoint, "StudentRepository", FakeStudentRepository)

    response = client.post(
        "/student/",
        json={
            "name": "Maria",
            "registration": "MAT-001",
            "classroom_id": 2,
            "active": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["registration"] == "MAT-001"


def test_create_test_uses_authenticated_user_as_creator(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 99}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 99}

    captured = {}

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def create_test(self, test):
            captured["created_by_user_id"] = test.created_by_user_id
            return {
                "id": 4,
                "name": test.name,
                "theme": test.theme,
                "application_date": date(2026, 3, 23),
                "created_by_user_id": test.created_by_user_id,
                "target_type": test.target_type.value,
                "created_at": datetime(2026, 3, 23, 11, 0, 0),
                "questions": [
                    {
                        "id": 1,
                        "enunciation": "Quanto e 2 + 2?",
                        "itens": ["3", "4", "5"],
                        "correct_item": 1,
                        "level": 1,
                        "contents": ["adicao"],
                        "dependencies": [],
                        "created_at": datetime(2026, 3, 23, 11, 0, 0),
                    }
                ],
            }

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)

    response = client.post(
        "/test/",
        json={
            "name": "Prova diagnostica",
            "theme": "Operacoes basicas",
            "application_date": "2026-03-23",
            "questions": [1],
        },
    )

    assert response.status_code == 200
    assert captured["created_by_user_id"] == 99
    assert response.json()["created_by_user_id"] == 99


def test_get_test_route_returns_test_payload(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor"}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_endpoint, "ensure_test_scope", lambda *_args, **_kwargs: None)

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def get_test(self, test_id):
            return {
                "id": test_id,
                "name": "Prova 1",
                "theme": "Equacoes",
                "application_date": date(2026, 3, 24),
                "created_by_user_id": 1,
                "target_type": "individual",
                "created_at": datetime(2026, 3, 23, 12, 0, 0),
                "questions": [
                    {
                        "id": 3,
                        "enunciation": "Resolva x + 2 = 5",
                        "itens": ["1", "2", "3"],
                        "correct_item": 2,
                        "level": 3,
                        "contents": ["equacao do primeiro grau"],
                        "dependencies": [],
                        "created_at": datetime(2026, 3, 23, 12, 0, 0),
                    }
                ],
            }

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)

    response = client.get("/test/1")

    assert response.status_code == 200
    assert response.json()["id"] == 1
    assert response.json()["questions"][0]["level"] == 3


def test_teacher_can_apply_library_test_to_own_classroom(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_endpoint, "ensure_test_scope", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(test_endpoint, "ensure_classroom_scope", lambda *_args, **_kwargs: None)

    captured = {}

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def apply_test(self, test_id, application, applied_by_user_id):
            captured["test_id"] = test_id
            captured["classroom_id"] = application.classroom_id
            captured["applied_by_user_id"] = applied_by_user_id
            return {
                "id": 22,
                "name": application.name or "Prova base",
                "theme": "Geometria",
                "kind": "application",
                "visibility": "library",
                "classroom_id": application.classroom_id,
                "source_test_id": test_id,
                "created_by_user_id": 1,
                "applied_by_user_id": applied_by_user_id,
                "application_date": date(2026, 3, 25),
                "target_type": application.target_type.value,
                "created_at": datetime(2026, 3, 23, 12, 0, 0),
                "questions": [],
            }

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)

    response = client.post(
        "/test/5/apply",
        json={
            "classroom_id": 2,
            "application_date": "2026-03-25",
            "name": "Aplicacao Turma A",
        },
    )

    assert response.status_code == 200
    assert captured == {"test_id": 5, "classroom_id": 2, "applied_by_user_id": 9}
    assert response.json()["kind"] == "application"
    assert response.json()["source_test_id"] == 5


def test_teacher_can_apply_library_test_to_student_in_scope(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_endpoint, "ensure_test_scope", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(test_endpoint, "ensure_student_scope", lambda *_args, **_kwargs: None)

    captured = {}

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def apply_test(self, test_id, application, applied_by_user_id):
            captured["test_id"] = test_id
            captured["student_id"] = application.student_id
            captured["target_type"] = application.target_type.value
            return {
                "id": 23,
                "name": application.name or "Aplicacao Individual",
                "theme": "Exponenciacao",
                "kind": "application",
                "visibility": "library",
                "classroom_id": 1,
                "student_id": application.student_id,
                "source_test_id": test_id,
                "template_group_id": 5,
                "version_number": 2,
                "created_by_user_id": 2,
                "applied_by_user_id": applied_by_user_id,
                "application_date": date(2026, 4, 2),
                "target_type": application.target_type.value,
                "created_at": datetime(2026, 4, 1, 12, 0, 0),
                "questions": [],
            }

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)

    response = client.post(
        "/test/5/apply",
        json={
            "student_id": 12,
            "target_type": "individual",
            "application_date": "2026-04-02",
            "name": "Aplicacao Individual",
        },
    )

    assert response.status_code == 200
    assert captured == {"test_id": 5, "student_id": 12, "target_type": "individual"}
    assert response.json()["student_id"] == 12
    assert response.json()["target_type"] == "individual"


def test_teacher_can_create_new_template_version(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_endpoint, "ensure_test_scope", lambda *_args, **_kwargs: None)

    captured = {}

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def create_template_version(self, test_id, version_data, created_by_user_id):
            captured["test_id"] = test_id
            captured["questions"] = version_data.questions
            captured["created_by_user_id"] = created_by_user_id
            return {
                "id": 30,
                "name": version_data.name or "Biblioteca Bloom - Exponenciacao v2",
                "theme": version_data.theme or "Exponenciacao",
                "kind": "template",
                "visibility": "library",
                "classroom_id": None,
                "student_id": None,
                "source_test_id": None,
                "template_group_id": 5,
                "version_number": 2,
                "created_by_user_id": created_by_user_id,
                "applied_by_user_id": None,
                "application_date": None,
                "target_type": "turma",
                "created_at": datetime(2026, 4, 1, 12, 0, 0),
                "questions": [],
            }

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)

    response = client.post(
        "/test/5/versions",
        json={
            "name": "Biblioteca Bloom - Exponenciacao v2",
            "questions": [1, 2, 3],
        },
    )

    assert response.status_code == 200
    assert captured == {"test_id": 5, "questions": [1, 2, 3], "created_by_user_id": 9}
    assert response.json()["kind"] == "template"
    assert response.json()["version_number"] == 2


def test_teacher_can_list_only_application_tests_in_scope(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    captured = {}

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def get_all_tests(self, current_user=None, accessible_classroom_ids=None, kind=None):
            captured["current_user"] = current_user
            captured["accessible_classroom_ids"] = accessible_classroom_ids
            captured["kind"] = kind
            return [
                {
                    "id": 31,
                    "name": "Aplicacao Turma A",
                    "theme": "Fracoes",
                    "kind": "application",
                    "visibility": "library",
                    "classroom_id": 2,
                    "source_test_id": 5,
                    "created_by_user_id": 1,
                    "applied_by_user_id": 9,
                    "application_date": date(2026, 3, 25),
                    "target_type": "turma",
                    "created_at": datetime(2026, 3, 23, 12, 0, 0),
                    "questions": [],
                }
            ]

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)
    monkeypatch.setattr(test_endpoint, "get_accessible_classroom_ids", lambda *_args, **_kwargs: {2, 3})

    response = client.get("/test/applications")

    assert response.status_code == 200
    assert response.json()[0]["kind"] == "application"
    assert captured["kind"] == "application"
    assert captured["accessible_classroom_ids"] == {2, 3}


def test_teacher_can_fetch_library_usage_metrics(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    captured = {}

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def get_library_usage_metrics(self, current_user=None, accessible_classroom_ids=None):
            captured["current_user"] = current_user
            captured["accessible_classroom_ids"] = accessible_classroom_ids
            return {
                "total_templates": 2,
                "used_templates": 1,
                "unused_templates": 1,
                "total_applications": 3,
                "templates_with_individual_applications": 1,
                "theme_distribution": [
                    {
                        "theme": "Exponenciacao",
                        "application_count": 3,
                        "template_count": 1,
                    }
                ],
                "bloom_level_distribution": [
                    {
                        "level": 3,
                        "application_count": 6,
                        "question_count": 2,
                    }
                ],
                "templates": [
                    {
                        "template_id": 5,
                        "template_group_id": 5,
                        "version_number": 2,
                        "name": "Template Expo v2",
                        "theme": "Exponenciacao",
                        "visibility": "library",
                        "application_count": 3,
                        "distinct_teacher_count": 2,
                        "classroom_application_count": 2,
                        "individual_application_count": 1,
                        "last_applied_at": "2026-04-01",
                        "bloom_level_distribution": [
                            {
                                "level": 3,
                                "application_count": 6,
                                "question_count": 2,
                            }
                        ],
                        "is_unused": False,
                    }
                ],
            }

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)
    monkeypatch.setattr(test_endpoint, "get_accessible_classroom_ids", lambda *_args, **_kwargs: {2, 3})

    response = client.get("/test/templates/metrics")

    assert response.status_code == 200
    assert captured["current_user"] == {"role": "professor", "user_id": 9}
    assert captured["accessible_classroom_ids"] == {2, 3}
    assert response.json()["total_templates"] == 2
    assert response.json()["templates"][0]["template_id"] == 5
    assert response.json()["templates"][0]["individual_application_count"] == 1


def test_teacher_can_generate_pdf_from_test_application(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_endpoint, "ensure_test_scope", lambda *_args, **_kwargs: None)

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def get_test(self, test_id):
            assert test_id == 22
            return SimpleNamespace(
                id=22,
                target_type="turma",
                student_id=None,
            )

    def fake_test_generate(test_id, student_names, student_ids, _db):
        assert test_id == 22
        assert student_names == ["Maria", "Joao"]
        assert student_ids == ["7", "8"]
        from io import BytesIO

        return BytesIO(b"zip-content")

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)
    monkeypatch.setattr(test_endpoint, "test_generate", fake_test_generate)

    response = client.get(
        "/test/applications/22/generate",
        headers={
            "test-id": "22",
            "student-name": "Maria,Joao",
            "student-id": "7,8",
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_pdf_generation_route_returns_domain_error_for_invalid_application(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_endpoint, "ensure_test_scope", lambda *_args, **_kwargs: None)

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def get_test(self, test_id):
            assert test_id == 5
            return SimpleNamespace(
                id=5,
                target_type="turma",
                student_id=None,
            )

    def fake_test_generate(*_args, **_kwargs):
        from app.core.exceptions import ValidationError

        raise ValidationError("A geração de PDF só pode ser feita a partir de uma aplicação de prova.")

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)
    monkeypatch.setattr(test_endpoint, "test_generate", fake_test_generate)

    response = client.get(
        "/test/applications/5/generate",
        headers={
            "test-id": "5",
            "student-name": "Maria",
            "student-id": "7",
        },
    )

    assert response.status_code == 400
    assert "aplicação de prova" in response.json()["detail"]


def test_teacher_can_update_test_response_score(client, monkeypatch):
    app.dependency_overrides[auth.require_academic_staff] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_response_endpoint, "ensure_test_response_scope", lambda *_args, **_kwargs: None)

    class FakeTestResponseRepository:
        def __init__(self, _db):
            pass

        def update_test_response(self, test_response):
            return {
                "id": test_response.id,
                "test_id": 1,
                "student_id": 5,
                "score": test_response.score,
                "responses": [1, 2, 3],
                "wrong_questions": [1],
                "attempt_date": date(2026, 3, 23),
            }

    monkeypatch.setattr(test_response_endpoint, "TestResponseRepository", FakeTestResponseRepository)

    response = client.put(
        "/test-response/",
        json={
            "id": 9,
            "score": 7.5,
        },
    )

    assert response.status_code == 200
    assert response.json()["score"] == 7.5


def test_get_student_analysis(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(student_endpoint, "ensure_student_scope", lambda *_args, **_kwargs: None)

    def fake_get_student_analysis(_db, student_id):
        return StudentAnalysis(
            student_id=student_id,
            student_name="Maria",
            classroom_id=2,
            overall_average=8.5,
            total_attempts=3,
            average_by_test=[],
            bloom_performance=[],
            errors_by_content=[],
            errors_by_bloom=[],
        )

    monkeypatch.setattr(student_endpoint, "get_student_analysis", fake_get_student_analysis)

    response = client.get("/student/7/analysis")

    assert response.status_code == 200
    assert response.json()["overall_average"] == 8.5


def test_get_classroom_analysis(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "diretor", "user_id": 5}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "diretor", "user_id": 5}

    monkeypatch.setattr(classroom_endpoint, "ensure_classroom_scope", lambda *_args, **_kwargs: None)

    def fake_get_classroom_analysis(_db, classroom_id):
        return ClassroomAnalysis(
            classroom_id=classroom_id,
            classroom_name="Turma A",
            school_year=2026,
            grade_level="8 ano",
            shift="manha",
            student_count=25,
            active_students=24,
            overall_average=7.8,
            average_by_test=[],
            bloom_performance=[],
            errors_by_content=[],
            errors_by_bloom=[],
            student_averages=[],
        )

    monkeypatch.setattr(classroom_endpoint, "get_classroom_analysis", fake_get_classroom_analysis)

    response = client.get("/classroom/2/analysis")

    assert response.status_code == 200
    assert response.json()["student_count"] == 25


def test_generate_student_reinforcement(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(student_endpoint, "ensure_student_scope", lambda *_args, **_kwargs: None)

    response = client.post("/student/7/analysis/reinforcement")

    assert response.status_code == 410
    assert "descontinuada" in response.json()["detail"]


def test_teacher_can_generate_pdf_for_individual_application_without_headers(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    monkeypatch.setattr(test_endpoint, "ensure_test_scope", lambda *_args, **_kwargs: None)

    class FakeTestRepository:
        def __init__(self, _db):
            pass

        def get_test(self, test_id):
            assert test_id == 22
            return SimpleNamespace(
                id=22,
                target_type="individual",
                student_id=7,
            )

    class FakeStudentRepository:
        def __init__(self, _db):
            pass

        def get_student(self, student_id):
            assert student_id == 7
            return SimpleNamespace(id=7, name="Maria")

    def fake_test_generate(test_id, student_names, student_ids, _db):
        assert test_id == 22
        assert student_names == ["Maria"]
        assert student_ids == ["7"]
        from io import BytesIO

        return BytesIO(b"zip-content")

    monkeypatch.setattr(test_endpoint, "TestRepository", FakeTestRepository)
    monkeypatch.setattr(test_endpoint, "StudentRepository", FakeStudentRepository)
    monkeypatch.setattr(test_endpoint, "test_generate", fake_test_generate)

    response = client.get("/test/applications/22/generate")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_teacher_cannot_access_student_outside_scope(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    def fake_ensure_student_scope(student_id, _db, _payload):
        raise HTTPException(status_code=403, detail=f"Sem acesso ao aluno {student_id}")

    monkeypatch.setattr(student_endpoint, "ensure_student_scope", fake_ensure_student_scope)

    response = client.get("/student/88")

    assert response.status_code == 403
    assert response.json()["detail"] == "Sem acesso ao aluno 88"


def test_teacher_cannot_update_grade_outside_scope(client, monkeypatch):
    app.dependency_overrides[auth.require_academic_staff] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    def fake_ensure_test_response_scope(test_response_id, _db, _payload):
        raise HTTPException(status_code=403, detail=f"Sem acesso a nota {test_response_id}")

    monkeypatch.setattr(test_response_endpoint, "ensure_test_response_scope", fake_ensure_test_response_scope)

    response = client.put(
        "/test-response/",
        json={
            "id": 12,
            "score": 6.0,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Sem acesso a nota 12"


def test_admin_can_assign_classroom_to_teacher(client, monkeypatch):
    app.dependency_overrides[auth.require_admin] = lambda: {"role": "admin", "user_id": 1}

    class FakeUserRepository:
        def __init__(self, _db):
            pass

        def add_classroom_to_user(self, user_id, classroom_id):
            return {
                "id": user_id,
                "username": "prof_math",
                "email": "prof@matbloom.com",
                "role": "professor",
                "classes": [
                    {
                        "id": classroom_id,
                        "name": "Turma A",
                        "school_year": 2026,
                        "grade_level": "8 ano",
                        "shift": "manha",
                        "active": True,
                        "students": [],
                    }
                ],
            }

    monkeypatch.setattr(user_endpoint, "UserRepository", FakeUserRepository)

    response = client.post("/user/9/classrooms/2")

    assert response.status_code == 200
    assert response.json()["classes"][0]["id"] == 2


def test_admin_can_remove_classroom_from_teacher(client, monkeypatch):
    app.dependency_overrides[auth.require_admin] = lambda: {"role": "admin", "user_id": 1}

    class FakeUserRepository:
        def __init__(self, _db):
            pass

        def remove_classroom_from_user(self, user_id, _classroom_id):
            return {
                "id": user_id,
                "username": "prof_math",
                "email": "prof@matbloom.com",
                "role": "professor",
                "classes": [],
            }

    monkeypatch.setattr(user_endpoint, "UserRepository", FakeUserRepository)

    response = client.delete("/user/9/classrooms/2")

    assert response.status_code == 200
    assert response.json()["classes"] == []


def test_teacher_can_list_own_classrooms(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    class FakeUserRepository:
        def __init__(self, _db):
            pass

        def list_user_classrooms(self, user_id):
            return [
                {
                    "id": 2,
                    "name": "Turma A",
                    "school_year": 2026,
                    "grade_level": "8 ano",
                    "shift": "manha",
                    "active": True,
                    "students": [],
                },
                {
                    "id": 3,
                    "name": "Turma B",
                    "school_year": 2026,
                    "grade_level": "9 ano",
                    "shift": "tarde",
                    "active": True,
                    "students": [],
                },
            ]

    monkeypatch.setattr(user_endpoint, "UserRepository", FakeUserRepository)

    response = client.get("/user/9/classrooms")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_teacher_cannot_list_other_teacher_classrooms(client, monkeypatch):
    app.dependency_overrides[auth.require_user] = lambda: {"role": "professor", "user_id": 9}
    app.dependency_overrides[auth.get_current_user_payload] = lambda: {"role": "professor", "user_id": 9}

    response = client.get("/user/10/classrooms")

    assert response.status_code == 403
    assert response.json()["detail"] == "Você só pode visualizar as próprias turmas."
