from app.api.schemas.student import Student

from pydantic import BaseModel
from typing import List

class ClassroomBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Turma.

        - Attributes:
            - name: str - Nome da turma.
    """
    name: str

class ClassroomCreate(ClassroomBase):
    """
        Esta classe representa o modelo de Turma para criação.

        - Attributes:
            - name: str - Nome da turma.
    """
    pass

class Classroom(ClassroomBase):
    """
        Esta classe representa o modelo de Turma para retorno.

        - Attributes:
            - id: int - ID da turma.
            - name: str - Nome da turma.
            - students: List[Student] - Lista de estudantes na turma.
    """
    id: int
    students: List[Student] = []

    model_config = {
        "from_attributes": True
    }