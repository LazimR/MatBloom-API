from app.db.models.base import Base
from sqlalchemy import String, Integer, ForeignKey, Date, DateTime, Float
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY
from app.db.models.connection import engine

class Question(Base):

    __tablename__ = "question"

    id:Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)  # Identificador único da questão
    enunciation:Mapped[str] = mapped_column(String,nullable=False)  # Texto da questão
    itens:Mapped[list[str]] = mapped_column(ARRAY(String),nullable=False)  # Lista de alternativas
    correct_item:Mapped[int] = mapped_column(Integer,nullable=True)  # Índice da alternativa correta
    level:Mapped[int] = mapped_column(Integer,nullable=False)  # Nível da Taxonomia de Bloom (1 a 6)
    contents:Mapped[list[str]] = mapped_column(ARRAY(String),nullable=True)  # Lista de conteúdos relacionados
    dependencies: Mapped[list["Question"]] = relationship(
        secondary="question_dependency",  # Tabela de relacionamento
        primaryjoin="Question.id == QuestionDependency.question_id",  # Junção primária
        secondaryjoin="Question.id == QuestionDependency.dependency_id",  # Junção secundária
        backref="dependents",  # Nome do backref para acessar questões que dependem desta
    )

class Test(Base):

    __tablename__ = "test"

    id:Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True)  # Identificador único da prova
    name:Mapped[str] = mapped_column(String,nullable=False)  # Nome da prova

    questions: Mapped[list["Question"]] = relationship(
        "Question",
        secondary="test_question",  # Nome da tabela auxiliar
        backref="tests"  # Permite acessar os testes associados a uma questão
    )

    test_responses: Mapped[list["TestResponse"]] = relationship("TestResponse", back_populates="test")
class TestQuestion(Base):
    __tablename__ = "test_question"

    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("test.id"), primary_key=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"), primary_key=True)

class Content(Base):
    __tablename__ = "content"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)

class QuestionContent(Base):
    __tablename__ = "question_content"

    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("question.id"), primary_key=True)
    content_id: Mapped[int] = mapped_column(Integer, ForeignKey("content.id"), primary_key=True)

class QuestionDependency(Base):
    __tablename__ = "question_dependency"

    question_id: Mapped[int] = mapped_column(Integer,ForeignKey("question.id"),primary_key=True)
    dependency_id: Mapped[int] = mapped_column(Integer,ForeignKey("question.id"),primary_key=True)

class Student(Base):
    __tablename__ = "student"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relacionamento com TestResponse (opcional, se você quiser acessar as respostas do aluno)
    test_responses: Mapped[list["TestResponse"]] = relationship("TestResponse", back_populates="student")


class TestResponse(Base):
    __tablename__ = "test_response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("test.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("student.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=True)  # Nota da prova
    responses: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)  # Respostas do aluno

    # Relacionamentos
    test: Mapped["Test"] = relationship("Test", back_populates="test_responses")
    student: Mapped["Student"] = relationship("Student", back_populates="test_responses")


def create_entities(engine) -> bool:
    """
    Cria no banco todas as entidades necessárias para o sistema
    """
    try:
        Base.metadata.create_all(engine)
        return True
    except Exception:
        return False
    

if __name__ == "__main__":
    from sqlalchemy import MetaData
    from sqlalchemy.schema import CreateTable

    # Criar metadados a partir das tabelas registradas na Base
    metadata = Base.metadata

# Gerar o script SQL
    with open("schema.sql", "w") as f:
        for table in metadata.sorted_tables:
            f.write(str(CreateTable(table).compile(engine)) + ";\n\n")

    print("Script SQL gerado em 'schema.sql'")


    if create_entities(engine):
        print("success")
    else:
        print("fail")
