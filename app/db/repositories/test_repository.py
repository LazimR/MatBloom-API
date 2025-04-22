from sqlalchemy.orm import Session, joinedload

from app.db.models.models import TestQuestion
from app.db.models.models import Test as TestModel
from app.db.models.models import Question as QuestionModel
from app.api.schemas.test import TestCreate
from app.api.schemas.test import Test as TestSchema
from app.api.schemas.question import Question as QuestionSchema

class TestRepository:
    """
        Esta classe é responsável por interagir com o banco de dados para operações relacionadas a testes.
        Ela fornece métodos para criar, ler e deletar testes, bem como para obter questões associadas a um teste.

        - Attributes:
            - db_session: Session - Sessão do banco de dados utilizada para realizar operações.
        
        - Funcs: 
            - get_test: Retorna as questões de um teste específico do banco de dados.
            - get_all_tests: Retorna todos os testes do banco de dados.
            - get_test_questions: Retorna todas as questões associadas a um teste específico.
            - create_test: Cria um novo teste no banco de dados com as questões associadas.
            - delete_test: Deleta um teste do banco de dados.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_test(self, test_id: int) -> TestSchema:
        """
            Retorna um teste específico do banco de dados.

            props:
                - test_id: int - ID do teste a ser retornado.

            return:
                - list_questions: list[Question] - Lista de questões associadas ao teste.

        """
        
        # Verifica se o teste existe no banco de dados
        db_test = self.db_session.query(TestModel).filter(TestModel.id == test_id).first()

        if db_test:
            questions = self.get_test_questions(test_id)
            list_questions = [
            QuestionSchema(
                **{k: v for k, v in question.__dict__.items() if k != "dependencies"},
                dependencies=[
                    QuestionSchema(**dependency.__dict__) for dependency in question.dependencies
                ]
            )
            for question in questions
        ]
            if len(list_questions) == 0:
                raise ValueError(f"Test with ID {test_id} has no questions.") 
        else:
            raise ValueError(f"Test with ID {test_id} does not exist.")
            

        return TestSchema(
            id=db_test.id,
            name=db_test.name,
            questions=list_questions
            )
    
    def get_all_tests(self) -> list[TestSchema]:
        """
        Retorna todos os testes do banco de dados.
        """
        # Carrega os testes com as questões associadas
        tests = self.db_session.query(TestModel).options(
        joinedload(TestModel.questions).joinedload(QuestionModel.dependencies)
    ).all()

        if not tests:
            raise ValueError("No tests found in the database.")

        list_test = [
        TestSchema(
            id=test.id,
            name=test.name,
            questions=[
                QuestionSchema(
                    **{k: v for k, v in question.__dict__.items() if k != "dependencies"},
                    dependencies=[
                        QuestionSchema(**dependency.__dict__) for dependency in question.dependencies
                    ]
                )
                for question in test.questions
            ]
        )
        for test in tests
    ]

        return list_test
    
    def get_test_questions(self, test_id: int) -> list[QuestionModel]:
        """
            Retorna todas as questões associadas a um teste específico.

            props:
                - test_id: int - ID do teste cujas questões serão retornadas.
            
            return:
                - list[Question] - Lista de questões associadas ao teste.

        """
        
        # Verifica se o teste existe no banco de dados
        db_test = self.db_session.query(TestModel).filter(TestModel.id == test_id).first()

        if not db_test:
            raise ValueError(f"Test with ID {test_id} does not exist.")

        # Retorna as questões associadas ao teste
        return self.db_session.query(QuestionModel).join(TestQuestion).filter(TestQuestion.test_id == test_id).all()
    
    def create_test(self, test: TestCreate) -> TestSchema:
        """
            Cria um novo teste no banco de dados com as questões associadas.

            props:
                - test: TestCreate - Objeto com os dados do teste a ser criado.
            
            return:
                - Test - Objeto Test criado no banco de dados.

        """

        # Cria o objeto Test sem as questões
        db_test = TestModel(**test.model_dump(exclude={"questions"}))

        # Adiciona o Test à sessão e gera o ID com flush
        self.db_session.add(db_test)
        self.db_session.flush()  # Gera o ID do Test sem confirmar a transação

        # Verifica se as questões existem no banco de dados
        for question_id in test.questions:
            question = self.db_session.query(QuestionModel).filter(QuestionModel.id == question_id).first()
            if not question:
                raise ValueError(f"Question with ID {question_id} does not exist.")

            # Adiciona a relação na tabela TestQuestion
            test_question = TestQuestion(test_id=db_test.id, question_id=question_id)
            self.db_session.add(test_question)

        # Confirma a transação
        self.db_session.commit()
        self.db_session.refresh(db_test)  # Atualiza o objeto Test com os dados finais
        return TestSchema(**db_test.dict())
    
    def delete_test(self, test_id: int) -> bool:
        """
            Deleta um teste do banco de dados.

            props:
                - test_id: int - ID do teste a ser deletado.

            return:
                - bool - True se o teste foi deletado com sucesso, raise caso contrário.
        """
        db_test = self.db_session.query(TestModel).filter(TestModel.id == test_id).first()
        if db_test:
            self.db_session.delete(db_test)
            self.db_session.commit()
        else:
            raise ValueError(f"Test with ID {test_id} does not exist.")
    
        return True
