from app.core.academic import ClassroomShift
from app.api.schemas.student import Student

from pydantic import BaseModel, Field
from typing import List


class ClassroomTeacher(BaseModel):
    id: int
    username: str
    email: str

    model_config = {
        "from_attributes": True
    }

class ClassroomBase(BaseModel):
    """
        Esta classe representa a base para o modelo de Turma.

        - Attributes:
            - name: str - Nome da turma.
    """
    name: str
    school_year: int
    grade_level: str
    shift: ClassroomShift
    active: bool = True

class ClassroomCreate(ClassroomBase):
    """
        Esta classe representa o modelo de Turma para criação.

        - Attributes:
            - name: str - Nome da turma.
    """
    pass


class ClassroomUpdate(BaseModel):
    id: int
    name: str | None = None
    school_year: int | None = None
    grade_level: str | None = None
    shift: ClassroomShift | None = None
    active: bool | None = None

class Classroom(ClassroomBase):
    """
        Esta classe representa o modelo de Turma para retorno.

        - Attributes:
            - id: int - ID da turma.
            - name: str - Nome da turma.
            - students: List[Student] - Lista de estudantes na turma.
    """
    id: int
    teacher_ids: List[int] = Field(default_factory=list)
    teachers: List[ClassroomTeacher] = Field(default_factory=list)
    students: List[Student] = Field(default_factory=list)

    model_config = {
        "from_attributes": True
    }
