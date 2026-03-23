from sqlalchemy.orm import Session
from app.api.security.auth import pwd_context

from app.core.exceptions import ConflictError, NotFoundError
from app.core.roles import UserRole
from app.api.schemas.classroom import Classroom as ClassroomSchema
from app.db.models.models import Classroom as ClassroomModel
from app.db.models.models import User as UserModel
from app.api.schemas.user import UserCreate, User as UserSchema
from app.api.schemas.user import UserLogin, UserUpdate, UserDelete

class UserRepository:
    """
    Esta classe é responsável por interagir com o banco de dados para operações relacionadas a usuários.
    Fornece métodos para criar, buscar e listar usuários.

    - Attributes:
        - db_session: Session - Sessão do banco de dados utilizada para realizar operações.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_user_by_username(self, username: str) -> UserSchema:
        db_user = self.get_user_model_by_username(username)
        if not db_user:
            raise NotFoundError(f"User with username '{username}' does not exist.")
        return UserSchema.model_validate(db_user)

    def get_user_by_email(self, email: str) -> UserSchema:
        db_user = self.db_session.query(UserModel).filter(UserModel.email == email).first()
        if not db_user:
            raise NotFoundError(f"User with email '{email}' does not exist.")
        return UserSchema.model_validate(db_user)

    def get_user_model_by_id(self, user_id: int) -> UserModel | None:
        return self.db_session.query(UserModel).filter(UserModel.id == user_id).first()

    def get_user_model_by_username(self, username: str) -> UserModel | None:
        return self.db_session.query(UserModel).filter(UserModel.username == username).first()

    def has_any_user(self) -> bool:
        return self.db_session.query(UserModel.id).first() is not None

    def list_users(self) -> list[UserSchema]:
        users = self.db_session.query(UserModel).all()
        return [UserSchema.model_validate(user) for user in users]
    
    def add_classroom_to_user(self, user_id: int, classroom_id: int):
        user = self.db_session.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise NotFoundError(f"User with ID {user_id} does not exist.")

        classroom = self.db_session.query(ClassroomModel).filter(ClassroomModel.id == classroom_id).first()
        if not classroom:
            raise NotFoundError(f"Classroom with ID {classroom_id} does not exist.")

        if user.role != UserRole.TEACHER.value:
            raise ConflictError("Apenas usuários com papel de professor podem ser vinculados a turmas.")

        if any(existing_classroom.id == classroom_id for existing_classroom in user.classes):
            raise ConflictError("O professor já está vinculado a esta turma.")

        user.classes.append(classroom)
        self.db_session.commit()
        self.db_session.refresh(user)
        return UserSchema.model_validate(user)

    def remove_classroom_from_user(self, user_id: int, classroom_id: int) -> UserSchema:
        user = self.db_session.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise NotFoundError(f"User with ID {user_id} does not exist.")

        classroom = self.db_session.query(ClassroomModel).filter(ClassroomModel.id == classroom_id).first()
        if not classroom:
            raise NotFoundError(f"Classroom with ID {classroom_id} does not exist.")

        if all(existing_classroom.id != classroom_id for existing_classroom in user.classes):
            raise NotFoundError("O professor não está vinculado a esta turma.")

        user.classes = [existing_classroom for existing_classroom in user.classes if existing_classroom.id != classroom_id]
        self.db_session.commit()
        self.db_session.refresh(user)
        return UserSchema.model_validate(user)

    def list_user_classrooms(self, user_id: int) -> list[ClassroomSchema]:
        user = self.db_session.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise NotFoundError(f"User with ID {user_id} does not exist.")

        return [ClassroomSchema.model_validate(classroom) for classroom in user.classes]

    def create_user(self, user: UserCreate) -> UserSchema:
        if self.get_user_model_by_username(user.username):
            raise ConflictError(f"User with username '{user.username}' already exists.")

        if self.db_session.query(UserModel).filter(UserModel.email == user.email).first():
            raise ConflictError(f"User with email '{user.email}' already exists.")

        hashed_password = pwd_context.hash(user.password)
        db_user = UserModel(
            username=user.username,
            email=user.email,
            password=hashed_password,
            role=user.role.value
        )
        self.db_session.add(db_user)
        self.db_session.commit()
        self.db_session.refresh(db_user)
        return UserSchema.model_validate(db_user)
    
    def authenticate_user(self, user:UserLogin) -> UserSchema | None:
        db_user = self.get_user_model_by_username(user.username)
        if db_user and pwd_context.verify(user.password, db_user.password):
            return UserSchema.model_validate(db_user)
        return None
    
    def delete_user(self, user_delete: UserDelete) -> bool:
        user = self.db_session.query(UserModel).filter(UserModel.id == user_delete.id).first()
        if not user:
            raise NotFoundError(f"User with ID {user_delete.id} does not exist.")
        self.db_session.delete(user)
        self.db_session.commit()
        return True

    def update_user(self, user_update: UserUpdate) -> UserSchema:
        user = self.get_user_model_by_id(user_update.id)
        if not user:
            raise NotFoundError(f"User with ID {user_update.id} does not exist.")

        if user_update.username is not None:
            existing_user = self.get_user_model_by_username(user_update.username)
            if existing_user and existing_user.id != user.id:
                raise ConflictError(f"User with username '{user_update.username}' already exists.")
            user.username = user_update.username
        if user_update.email is not None:
            existing_email = self.db_session.query(UserModel).filter(UserModel.email == user_update.email).first()
            if existing_email and existing_email.id != user.id:
                raise ConflictError(f"User with email '{user_update.email}' already exists.")
            user.email = user_update.email
        if user_update.password is not None:
            user.password = pwd_context.hash(user_update.password)
        if user_update.role is not None:
            user.role = user_update.role.value

        self.db_session.commit()
        self.db_session.refresh(user)
        return UserSchema.model_validate(user)
