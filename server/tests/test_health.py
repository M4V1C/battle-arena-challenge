from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ruta_inexistente_devuelve_404():
    response = client.get("/no-existe")
    assert response.status_code == 404