from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db.models.models import TestResponse as TestResponseModel
from app.api.schemas.test_response import TestResponseCreate, TestResponse, TestResponseUpdate
from app.db.models.models import Student as StudentModel
from app.db.models.models import Test as TestModel

class TestResponseRepository:
    """
        Esta classe é responsável por interagir com o banco de dados para operações relacionadas a respostas de testes.
        Ela fornece métodos para criar, ler e deletar respostas de testes.

        - Attributes:
            - db_session: Session - Sessão do banco de dados utilizada para realizar operações.
        
        - Funcs: 
            - get_test_response: Retorna uma resposta de teste específica do banco de dados.
            - get_all_test_responses: Retorna todas as respostas de teste do banco de dados.
            - create_test_response: Cria uma nova resposta de teste no banco de dados.
            - delete_test_response: Deleta uma resposta de teste do banco de dados.
    """

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_test_response(self, test_response_id: int) -> TestResponse:
        """
            Retorna uma resposta de teste específica do banco de dados.

            props:
                - test_response_id: int - ID da resposta de teste a ser retornada.

            return:
                - TestResponse - Resposta de teste correspondente ao ID fornecido.
        """
        db_test_response = self.db_session.query(TestResponseModel).filter(TestResponseModel.id == test_response_id).first()
        if db_test_response:
            return TestResponse.model_validate(db_test_response)
        else:
            raise NotFoundError(f"Test response with ID {test_response_id} does not exist.")
    
    def get_all_test_responses(self, classroom_ids: set[int] | None = None) -> list[TestResponse]:
        """
            Retorna todas as respostas de teste do banco de dados.

            return:
                - list[TestResponse] - Lista de todas as respostas de teste.
        """
        query = self.db_session.query(TestResponseModel)
        if classroom_ids is not None:
            query = query.join(StudentModel).filter(StudentModel.classroom_id.in_(classroom_ids))
        db_test_responses = query.all()
        return [TestResponse.model_validate(test_response) for test_response in db_test_responses]
    
    def create_test_response(self, test_response: TestResponseCreate) -> TestResponse:
        """
            Cria uma nova resposta de teste no banco de dados.

            props:
                - test_response: TestResponseCreate - Dados da resposta de teste a ser criada.

            return:
                - TestResponse - Resposta de teste criada.
        """
        if not self.db_session.query(TestModel).filter(TestModel.id == test_response.test_id).first():
            raise NotFoundError(f"Test with ID {test_response.test_id} does not exist.")
        if not self.db_session.query(StudentModel).filter(StudentModel.id == test_response.student_id).first():
            raise NotFoundError(f"Student with ID {test_response.student_id} does not exist.")

        db_test_response = TestResponseModel(**test_response.model_dump())
        self.db_session.add(db_test_response)
        self.db_session.commit()
        self.db_session.refresh(db_test_response)
        return TestResponse.model_validate(db_test_response)

    def update_test_response(self, test_response_update: TestResponseUpdate) -> TestResponse:
        db_test_response = self.db_session.query(TestResponseModel).filter(TestResponseModel.id == test_response_update.id).first()
        if not db_test_response:
            raise NotFoundError(f"Test response with ID {test_response_update.id} does not exist.")

        for field in ("score", "responses", "wrong_questions", "attempt_date"):
            value = getattr(test_response_update, field)
            if value is not None:
                setattr(db_test_response, field, value)

        self.db_session.commit()
        self.db_session.refresh(db_test_response)
        return TestResponse.model_validate(db_test_response)
    
    def delete_test_response(self, test_response_id: int) -> bool:
        """
            Deleta uma resposta de teste do banco de dados.

            props:
                - test_response_id: int - ID da resposta de teste a ser deletado.

            return:
                - bool - True se a resposta de teste foi deletada com sucesso, False caso contrário.
        """
        db_test_response = self.db_session.query(TestResponseModel).filter(TestResponseModel.id == test_response_id).first()
        if db_test_response:
            self.db_session.delete(db_test_response)
            self.db_session.commit()
            return True
        else:
            return False
