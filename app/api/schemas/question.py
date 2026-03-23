"""
    Este módulo contém os modelos de dados para o Questões.

    classes:
        - QuestionBase: Classe base para as questões, contendo os campos comuns.
        - QuestionCreate: Classe para criar novas questões, herda de QuestionBase.
        - Question: Classe para representar questões existentes, herda de QuestionBase e inclui o ID da questão.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator

class QuestionBase(BaseModel):
    """
        Classe base para as questões, contendo os campos comuns.

        - Attributes:
            - enunciation: str - Texto da questão.
            - itens: List[str] - Lista de alternativas.
            - correct_item: int - Índice da alternativa correta.
            - level: int - Nível da Taxonomia de Bloom (1 a 6).
            - contents: List[str] - Lista de conteúdos relacionados.
            - dependencies: Optional[List[str]] - Lista de IDs de questões que dependem desta.
    """
    enunciation: str
    itens: List[str]
    correct_item: int
    level: int
    contents: List[str] = Field(default_factory=list)
    dependencies: List[int] = Field(default_factory=list)

class QuestionCreate(QuestionBase):
    """
        Classe para criar novas questões, herda de QuestionBase.

        - Attributes:
            - enunciation: str - Texto da questão.
            - itens: List[str] - Lista de alternativas.
            - correct_item: int - Índice da alternativa correta.
            - level: int - Nível da Taxonomia de Bloom (1 a 6).
            - contents: List[str] - Lista de conteúdos relacionados.
            - dependencies: Optional[List[str]] - Lista de IDs de questões que dependem desta.
    """
    @model_validator(mode="after")
    def validate_question(self):
        if len(self.itens) < 2:
            raise ValueError("A questão deve possuir ao menos duas alternativas.")
        if self.correct_item < 0 or self.correct_item >= len(self.itens):
            raise ValueError("correct_item deve apontar para uma alternativa válida.")
        if self.level < 1 or self.level > 6:
            raise ValueError("level deve estar entre 1 e 6.")
        return self

class QuestionDelete(BaseModel):
    """
        Classe para deletar questões, herda de QuestionBase.

        - Attributes:
            - id: int - ID da questão a ser deletada.
    """
    id: int

class Question(QuestionBase):
    """
        Classe para representar questões existentes, herda de QuestionBase e inclui o ID da questão.

        - Attributes:
            - id: int - ID da questão.
            - enunciation: str - Texto da questão.
            - itens: List[str] - Lista de alternativas.
            - correct_item: int - Índice da alternativa correta.
            - level: int - Nível da Taxonomia de Bloom (1 a 6).
            - contents: List[str] - Lista de conteúdos relacionados.
            - dependencies: Optional[List[str]] - Lista de IDs de questões que dependem desta.
    """
    id: int
    created_at: datetime

    model_config = {
        "from_attributes": True
    }
