from app.db.models.base import Base
from sqlalchemy import String, Integer, ForeignKey, Date, DateTime, Float, Table, Column
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import ARRAY
from app.db.models.connection import engine

class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enunciation: Mapped[str] = mapped_column(String, nullable=False)
    itens: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    correct_item: Mapped[int] = mapped_column(Integer, nullable=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)

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

    classroom_id: Mapped[int] = mapped_column(ForeignKey("classroom.id"), nullable=False)

    classroom: Mapped["Classroom"] = relationship("Classroom", back_populates="students")

    test_responses: Mapped[list["TestResponse"]] = relationship("TestResponse", back_populates="student")


class TestResponse(Base):
    __tablename__ = "test_response"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    test_id: Mapped[int] = mapped_column(Integer, ForeignKey("test.id"), nullable=False)
    student_id: Mapped[int] = mapped_column(Integer, ForeignKey("student.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=True)  # Nota da prova
    responses: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False)  # Respostas do aluno
    wrong_questions: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=True)  # Questões erradas
    # Relacionamentos
    test: Mapped["Test"] = relationship("Test", back_populates="test_responses")
    student: Mapped["Student"] = relationship("Student", back_populates="test_responses")


user_classroom_association = Table(
    "user_classroom",
    Base.metadata,
    Column("user_id", ForeignKey("user.id"), primary_key=True),
    Column("classroom_id", ForeignKey("classroom.id"), primary_key=True)
)

class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    acess_level: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relação muitos-para-muitos com Classroom
    classes: Mapped[list["Classroom"]] = relationship(
        "Classroom",
        secondary=user_classroom_association,
        back_populates="users"
    )

class Classroom(Base):
    __tablename__ = "classroom"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Relação muitos-para-muitos com User
    users: Mapped[list["User"]] = relationship(
        "User",
        secondary=user_classroom_association,
        back_populates="classes"
    )

    students: Mapped[list["Student"]] = relationship("Student", back_populates="classroom")

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
