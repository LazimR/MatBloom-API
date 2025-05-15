from app.api.schemas.classroom import Classroom

from pydantic import BaseModel, EmailStr
from typing import Optional, List

class UserBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Usuário.

        - Attributes:
            - username: str - Nome de usuário.
            - email: EmailStr - Endereço de e-mail do usuário.
            - password: str - Senha do usuário.
    """
    username: str
    email: EmailStr
    password: str

class UserCreate(UserBase):
    """
        Esta classe representa o modelo de Usuário para criação.

        - Attributes:
            - username: str - Nome de usuário.
            - email: EmailStr - Endereço de e-mail do usuário.
            - password: str - Senha do usuário.
    """
    pass

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

    class Config:
        orm_mode = True