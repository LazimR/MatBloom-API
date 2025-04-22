from fastapi.testclient import TestClient
from app.main import app  # Substitua pelo caminho correto para sua aplicação FastAPI

client = TestClient(app)

def test_get_test():
    """
    Testa o endpoint GET /test/{test_id}.
    """
    test_id = 1
    response = client.get(f"/tests/{test_id}")
    print(response.json())  # Adicione esta linha para depuração
    assert response.status_code == 200