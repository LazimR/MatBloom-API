from datetime import datetime, timedelta
from typing import Optional
import os
import bcrypt
from dotenv import load_dotenv

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from app.db.models.connection import get_session
from app.db.models.models import Classroom, Student, Test, TestResponse, User
from app.core.roles import UserRole
from app.core.academic import TestKind, TestVisibility

load_dotenv()

secret_key = os.getenv("SECRET_KEY")

jwt_algorithm = os.getenv("JWT_ALGORITHM")

access_token_expire_minutes = os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")
auth_cookie_name = os.getenv("AUTH_COOKIE_NAME", "matbloom_access_token")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=int(access_token_expire_minutes)))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, secret_key, algorithm=jwt_algorithm)
    return encoded_jwt

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, secret_key, algorithms=[jwt_algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

def extract_access_token_from_request(request: Request) -> str | None:
    authorization = request.headers.get("Authorization")
    if authorization:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token:
            return token

    return request.cookies.get(auth_cookie_name)

def get_current_user_payload(request: Request):
    token = extract_access_token_from_request(request)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return verify_access_token(token)

def get_optional_current_user_payload(request: Request):
    token = extract_access_token_from_request(request)
    if token is None:
        return None
    return verify_access_token(token)

def require_roles(*roles: UserRole):
    allowed_roles = {role.value for role in roles}

    def dependency(payload: dict = Depends(get_current_user_payload)):
        if payload.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem permissão para executar esta ação.",
            )
        return payload

    return dependency

require_admin = require_roles(UserRole.ADMIN)
require_director_or_admin = require_roles(UserRole.ADMIN, UserRole.DIRECTOR)
require_teacher_or_admin = require_roles(UserRole.ADMIN, UserRole.TEACHER)
require_academic_staff = require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)

require_user = require_roles(UserRole.ADMIN, UserRole.DIRECTOR, UserRole.TEACHER)


def get_accessible_classroom_ids(db: Session, payload: dict) -> set[int] | None:
    if payload.get("role") != UserRole.TEACHER.value:
        return None

    user = (
        db.query(User)
        .options(joinedload(User.classes))
        .filter(User.id == payload.get("user_id"))
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário autenticado não encontrado.",
        )

    return {classroom.id for classroom in user.classes}


def ensure_classroom_scope(classroom_id: int, db: Session, payload: dict):
    accessible_classroom_ids = get_accessible_classroom_ids(db, payload)
    if accessible_classroom_ids is None:
        return

    if classroom_id not in accessible_classroom_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta turma.",
        )


def ensure_student_scope(student_id: int, db: Session, payload: dict):
    accessible_classroom_ids = get_accessible_classroom_ids(db, payload)
    if accessible_classroom_ids is None:
        return

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Student with ID {student_id} does not exist.",
        )

    if student.classroom_id not in accessible_classroom_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a este aluno.",
        )


def ensure_test_response_scope(test_response_id: int, db: Session, payload: dict):
    accessible_classroom_ids = get_accessible_classroom_ids(db, payload)
    if accessible_classroom_ids is None:
        return

    test_response = (
        db.query(TestResponse)
        .options(joinedload(TestResponse.student))
        .filter(TestResponse.id == test_response_id)
        .first()
    )
    if not test_response:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test response with ID {test_response_id} does not exist.",
        )

    if test_response.student.classroom_id not in accessible_classroom_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a esta nota.",
        )


def ensure_test_scope(test_id: int, db: Session, payload: dict):
    if payload.get("role") != UserRole.TEACHER.value:
        return

    db_test = db.query(Test).filter(Test.id == test_id).first()
    if not db_test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test with ID {test_id} does not exist.",
        )

    if db_test.kind == TestKind.APPLICATION.value:
        accessible_classroom_ids = get_accessible_classroom_ids(db, payload) or set()
        if db_test.classroom_id not in accessible_classroom_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Você não tem acesso a esta aplicação de prova.",
            )
        return

    if db_test.visibility in {TestVisibility.LIBRARY.value, TestVisibility.SHARED.value}:
        return

    if db_test.created_by_user_id != payload.get("user_id"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem acesso a este modelo de prova.",
        )
