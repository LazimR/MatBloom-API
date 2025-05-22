from app.api.schemas.classroom import Classroom

from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional, List

class UserBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Usuário.

        - Attributes:
            - username: str - Nome de usuário.
            - email: EmailStr - Endereço de e-mail do usuário.
            - password: str - Senha do usuário.
            - acess_level: int - Nível de acesso do usuário (1 e 2).
    """
    username: str
    email: EmailStr
    password: str
    acess_level: int = 2

class UserCreate(UserBase):
    """
        Esta classe representa o modelo de Usuário para criação.

        - Attributes:
            - username: str - Nome de usuário.
            - email: EmailStr - Endereço de e-mail do usuário.
            - password: str - Senha do usuário.
            - acess_level: int - Nível de acesso do usuário (1 e 2).
    """

    pass

class UserUpdate(BaseModel):
    """
        Esta classe representa o modelo de Usuário para atualização.

        - Attributes:
            - username: Optional[str] - Nome de usuário.
            - email: Optional[EmailStr] - Endereço de e-mail do usuário.
            - password: Optional[str] - Senha do usuário.
    """
    id: int
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_field_modified(self):
        if self.username is None and self.email is None and self.password is None:
            raise ValueError("Pelo menos um dos campos username, email ou password deve ser modificado.")
        return self

class UserDelete(BaseModel):
    """
        Esta classe representa o modelo de Usuário para deleção.

        - Attributes:
            - id: int - ID do usuário.
    """
    id: int

class UserLogin(BaseModel):
    """
        Esta classe representa o modelo de Usuário para login.

        - Attributes:
            - username: str - Nome de usuário.
            - password: str - Senha do usuário.
    """
    username: str
    password: str

class User(UserBase):
    """
        Esta classe representa o modelo de Usuário para retorno.

        - Attributes:
            - id: int - ID do usuário.
            - username: str - Nome de usuário.
            - email: EmailStr - Endereço de e-mail do usuário.
            - password: str - Senha do usuário.
    """
    id: int
    classes: List[Classroom] = []

    model_config = {
        "from_attributes": True
    }