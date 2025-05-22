"""
    Este módulo contém os modelos de dados para o Questões.

    classes:
        - QuestionBase: Classe base para as questões, contendo os campos comuns.
        - QuestionCreate: Classe para criar novas questões, herda de QuestionBase.
        - Question: Classe para representar questões existentes, herda de QuestionBase e inclui o ID da questão.
"""

from pydantic import BaseModel
from typing import List, Optional

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
    contents: Optional[List[str]] = []
    dependencies: Optional[List[int]] = []

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

    pass

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

    model_config = {
        "from_attributes": True
    }