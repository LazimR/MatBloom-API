from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm


from app.api.schemas.classroom import Classroom as ClassroomSchema
from app.db.models.connection import get_session
from app.db.repositories.user_repository import UserRepository
from app.api.schemas.user import User as UserSchema, UserCreate, UserUpdate, UserDelete, UserLogin
from app.api.security.auth import (
    create_access_token,
    get_current_user_payload,
    get_optional_current_user_payload,
    require_admin,
    require_user,
)
from app.core.roles import UserRole

router = APIRouter()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    repo = UserRepository(db)
    db_user = repo.authenticate_user(UserLogin(username=form_data.username, password=form_data.password))
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    access_token = create_access_token(
        data={"sub": db_user.username, "role": db_user.role, "user_id": db_user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/", response_model=UserSchema)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_session),
    current_user: dict | None = Depends(get_optional_current_user_payload),
):
    repo = UserRepository(db)
    if repo.has_any_user():
        if current_user is None or current_user.get("role") != UserRole.ADMIN.value:
            raise HTTPException(status_code=403, detail="Apenas administradores podem criar usuários.")
    return repo.create_user(user)

@router.get("/", response_model=list[UserSchema], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_session)):
    repo = UserRepository(db)
    return repo.list_users()

@router.get("/{username}", response_model=UserSchema, dependencies=[Depends(require_user)])
def get_user(
    username: str,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = UserRepository(db)
    if current_user.get("role") != UserRole.ADMIN.value and current_user.get("sub") != username:
        raise HTTPException(status_code=403, detail="Você só pode visualizar os próprios dados.")
    return repo.get_user_by_username(username)

@router.put("/", response_model=UserSchema, dependencies=[Depends(require_user)])
def update_user(
    user: UserUpdate,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    repo = UserRepository(db)
    target_user = repo.get_user_model_by_id(user.id)
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User with ID {user.id} does not exist.")

    is_admin = current_user.get("role") == UserRole.ADMIN.value
    is_self = current_user.get("user_id") == user.id

    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="Você só pode editar os próprios dados.")

    if not is_admin and user.role is not None:
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar o papel de um usuário.")

    return repo.update_user(user)

@router.delete("/", dependencies=[Depends(require_admin)])
def delete_user(user: UserDelete, db: Session = Depends(get_session)):
    repo = UserRepository(db)
    repo.delete_user(user)
    return {"detail": "Usuário deletado com sucesso"}


@router.get("/{user_id}/classrooms", response_model=list[ClassroomSchema], dependencies=[Depends(require_user)])
def list_user_classrooms(
    user_id: int,
    db: Session = Depends(get_session),
    current_user: dict = Depends(get_current_user_payload),
):
    if current_user.get("role") != UserRole.ADMIN.value and current_user.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="Você só pode visualizar as próprias turmas.")

    repo = UserRepository(db)
    return repo.list_user_classrooms(user_id)


@router.post("/{user_id}/classrooms/{classroom_id}", response_model=UserSchema, dependencies=[Depends(require_admin)])
def add_classroom_to_user(user_id: int, classroom_id: int, db: Session = Depends(get_session)):
    repo = UserRepository(db)
    return repo.add_classroom_to_user(user_id, classroom_id)


@router.delete("/{user_id}/classrooms/{classroom_id}", response_model=UserSchema, dependencies=[Depends(require_admin)])
def remove_classroom_from_user(user_id: int, classroom_id: int, db: Session = Depends(get_session)):
    repo = UserRepository(db)
    return repo.remove_classroom_from_user(user_id, classroom_id)
