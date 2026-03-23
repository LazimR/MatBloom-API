from sqlalchemy.orm import Session

from app.api.schemas.question import Question as QuestionSchema, QuestionCreate, QuestionDelete
from app.core.exceptions import NotFoundError, OperationError, ValidationError
from app.db.models.models import Question as QuestionModel, QuestionDependency, Content, QuestionContent

class QuestionRepository:
    def __init__(self,db_session:Session) -> None:
        self.db_session = db_session
    

    def get_all_questions(self) -> list[QuestionSchema]:
        db_questions = self.db_session.query(QuestionModel).all()

        if not db_questions:
            raise NotFoundError("Não há nenhuma questão cadastrada.")
        
        return [self._build_question_schema(question) for question in db_questions]
    
    def get_question(self, question_id:int) -> QuestionSchema:
        db_question = self.db_session.query(QuestionModel).filter(QuestionModel.id == question_id).first()

        if not db_question:
            raise NotFoundError(f"Questão com ID {question_id} não existe.")
        
        return self._build_question_schema(db_question)
    
    def create_question(self, question_data: QuestionCreate) -> QuestionSchema:
        db_question = QuestionModel(
            enunciation=question_data.enunciation,
            itens=question_data.itens,
            correct_item=question_data.correct_item,
            level=question_data.level
        )
        self.db_session.add(db_question)
        self.db_session.commit()
        self.db_session.refresh(db_question)

        # Ligar conteúdos (por nome)
        for content_name in question_data.contents:
            content = self.db_session.query(Content).filter_by(name=content_name).first()
            if not content:
                content = Content(name=content_name)
                self.db_session.add(content)
                self.db_session.commit()
                self.db_session.refresh(content)

            relation = QuestionContent(
                question_id=db_question.id,
                content_id=content.id
            )
            self.db_session.add(relation)

        # Ligar dependências
        for dep_id in question_data.dependencies:
            if dep_id == db_question.id:
                raise ValidationError("Uma questão não pode depender dela mesma.")
            dep = QuestionDependency(
                question_id=db_question.id,
                dependency_id=dep_id
            )
            self.db_session.add(dep)

        self.db_session.commit()
        self.db_session.refresh(db_question)
        return self._build_question_schema(db_question)


    
    def delete_question(self, question: QuestionDelete) -> bool:
        db_question = self.db_session.query(QuestionModel).filter(QuestionModel.id == question.id).first()

        if not db_question:
            raise NotFoundError(f"Questão com ID {question.id} não existe.")
        
        try:
            self.db_session.delete(db_question)
            self.db_session.commit()
        except Exception as e:
            self.db_session.rollback()
            raise OperationError(f"Erro ao deletar questão: {e}")
        
        return True

    def _build_question_schema(self, question: QuestionModel) -> QuestionSchema:
        return QuestionSchema(
            id=question.id,
            enunciation=question.enunciation,
            itens=question.itens,
            correct_item=question.correct_item,
            level=question.level,
            contents=[content.name for content in question.contents],
            dependencies=[dependency.id for dependency in question.dependencies],
            created_at=question.created_at,
        )
    
    
