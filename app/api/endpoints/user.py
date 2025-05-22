from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm


from app.db.models.connection import get_session
from app.db.repositories.user_repository import UserRepository
from app.api.schemas.user import User as UserSchema, UserCreate, UserUpdate, UserDelete, UserLogin
from app.api.security.auth import create_access_token, require_admin, require_user

router = APIRouter()

@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_session)):
    repo = UserRepository(db)
    db_user = repo.authenticate_user(UserLogin(username=form_data.username, password=form_data.password))
    if not db_user:
        raise HTTPException(status_code=401, detail="Usuário ou senha inválidos")

    access_token = create_access_token(
        data={"sub": db_user.username, "acess_level": db_user.acess_level}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/", response_model=UserSchema)
def create_user(user: UserCreate, db: Session = Depends(get_session)):
    repo = UserRepository(db)
    return repo.create_user(user)

@router.get("/", response_model=list[UserSchema], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_session)):
    repo = UserRepository(db)
    return repo.list_users()

@router.get("/{username}", response_model=UserSchema, dependencies=[Depends(require_user)])
def get_user(username: str, db: Session = Depends(get_session)):
    repo = UserRepository(db)
    return repo.get_user_by_username(username)

@router.put("/", response_model=UserSchema, dependencies=[Depends(require_user)])
def update_user(user: UserUpdate, db: Session = Depends(get_session)):
    repo = UserRepository(db)
    return repo.update_user(user)

@router.delete("/", dependencies=[Depends(require_admin)])
def delete_user(user: UserDelete, db: Session = Depends(get_session)):
    repo = UserRepository(db)
    repo.delete_user(user)
    return {"detail": "Usuário deletado com sucesso"}