"""
Tests de criterios de aceptación Gherkin:
  HU-02 Escenario 1: Almacenamiento exitoso
  HU-02 Escenario 2: Datos incompletos → 422
  HU-03 Escenario 1: Datos en rango válido → aceptados
  HU-03 Escenario 2: Datos fuera de rango → 400, no almacenados
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.posture_capture.application.commands.save_reading_handler import SaveReadingHandler
from src.posture_capture.domain.entities.posture_reading import PostureReading
from src.posture_capture.interfaces.rest import readings_router

VALID_PAYLOAD = {
    "vest_id": "vest-001",
    "cervical": [0.1, 0.2, 9.8],
    "dorsal": [0.05, 0.1, 9.9],
    "lumbar": [0.0, 0.15, 9.7],
}


class _InMemoryRepo:
    def __init__(self) -> None:
        self.saved: list[PostureReading] = []

    async def save(self, reading: PostureReading) -> None:
        self.saved.append(reading)


class _StubMLClient:
    async def classify(self, reading: PostureReading) -> tuple[str, float]:
        return "adequate", 0.95


@pytest.fixture
def client_and_repo():
    repo = _InMemoryRepo()
    handler = SaveReadingHandler(repo, _StubMLClient())
    app.dependency_overrides[readings_router.get_handler] = lambda: handler
    with TestClient(app) as c:
        yield c, repo
    app.dependency_overrides.clear()


# HU-02 Escenario 1 — Almacenamiento exitoso
def test_almacenamiento_exitoso(client_and_repo):
    client, repo = client_and_repo
    response = client.post("/api/v1/readings", json=VALID_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["posture_class"] == "adequate"
    assert body["confidence"] == 0.95
    assert "id" in body
    assert len(repo.saved) == 1


# HU-02 Escenario 2 — Datos incompletos (falta campo requerido)
def test_datos_incompletos_no_almacenados(client_and_repo):
    client, repo = client_and_repo
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "dorsal"}
    response = client.post("/api/v1/readings", json=payload)
    assert response.status_code == 422
    assert len(repo.saved) == 0


# HU-03 Escenario 1 — Datos dentro de rango ±16g → aceptados
def test_datos_en_rango_valido_aceptados(client_and_repo):
    client, repo = client_and_repo
    payload = {**VALID_PAYLOAD, "dorsal": [0.0, 0.0, 9.81]}
    response = client.post("/api/v1/readings", json=payload)
    assert response.status_code == 201
    assert len(repo.saved) == 1


# HU-03 Escenario 2 — Datos fuera de rango → 400, no almacenados
def test_datos_fuera_de_rango_retornan_400(client_and_repo):
    client, repo = client_and_repo
    payload = {**VALID_PAYLOAD, "dorsal": [0.0, 0.0, 20.0]}
    response = client.post("/api/v1/readings", json=payload)
    assert response.status_code == 400
    assert "rango" in response.json()["detail"].lower()
    assert len(repo.saved) == 0
