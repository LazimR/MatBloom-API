from sqlalchemy.orm import Session, joinedload

from app.db.models.models import TestResponse as TestResponseModel
from app.api.schemas.test_response import TestResponseCreate, TestResponse

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
            return TestResponse.dict(**db_test_response.dict())
        else:
            raise ValueError(f"Test response with ID {test_response_id} does not exist.")
    
    def get_all_test_responses(self) -> list[TestResponse]:
        """
            Retorna todas as respostas de teste do banco de dados.

            return:
                - list[TestResponse] - Lista de todas as respostas de teste.
        """
        db_test_responses = self.db_session.query(TestResponseModel).all()
        return [TestResponse.dict(**test_response.dict()) for test_response in db_test_responses]
    
    def create_test_response(self, test_response: TestResponseCreate) -> TestResponse:
        """
            Cria uma nova resposta de teste no banco de dados.

            props:
                - test_response: TestResponseCreate - Dados da resposta de teste a ser criada.

            return:
                - TestResponse - Resposta de teste criada.
        """
        db_test_response = TestResponseModel(**test_response.dict())
        self.db_session.add(db_test_response)
        self.db_session.commit()
        self.db_session.refresh(db_test_response)
        return TestResponse.dict(**db_test_response.dict())
    
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