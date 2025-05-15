from sqlalchemy.orm import Session
from app.db.models.models import Classroom as ClassroomModel
from app.db.models.models import User as UserModel
from app.api.schemas.user import UserCreate, User as UserSchema

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
        db_user = self.db_session.query(UserModel).filter(UserModel.username == username).first()
        if not db_user:
            raise ValueError(f"User with username '{username}' does not exist.")
        return UserSchema.model_validate(db_user)

    def get_user_by_email(self, email: str) -> UserSchema:
        db_user = self.db_session.query(UserModel).filter(UserModel.email == email).first()
        if not db_user:
            raise ValueError(f"User with email '{email}' does not exist.")
        return UserSchema.model_validate(db_user)

    def list_users(self) -> list[UserSchema]:
        users = self.db_session.query(UserModel).all()
        return [UserSchema.model_validate(user) for user in users]
    
    def add_classroom_to_user(self, user_id: int, classroom_id: int):
        user = self.db_session.query(UserModel).filter(UserModel.id == user_id).first()
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist.")

        classroom = self.db_session.query(ClassroomModel).filter(ClassroomModel.id == classroom_id).first()
        if not classroom:
            raise ValueError(f"Classroom with ID {classroom_id} does not exist.")

        user.classes.append(classroom)
        self.db_session.commit()
        self.db_session.refresh(user)
        return user

    def create_user(self, user: UserCreate) -> UserSchema:
        db_user = UserModel(**user.model_dump())
        self.db_session.add(db_user)
        self.db_session.commit()
        self.db_session.refresh(db_user)
        return UserSchema.model_validate(db_user)