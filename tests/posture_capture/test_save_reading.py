"""
Tests de criterios de aceptación:
  HU-01 Happy : POST /readings con battery_percent → 201, battery almacenada
  HU-01 Unhappy: POST sin battery_percent → usa default 100%, igual 201
  HU-02 Happy : JSON válido con 3 sensores → 201, almacenado en repo
  HU-02 Unhappy: campo faltante → 422, no almacenado
  HU-03 Happy : valores dentro de ±16g → 201
  HU-03 Unhappy: valor fuera de ±16g → 400, no almacenado
  HU-06 Happy : GET /readings/latest → devuelve última lectura
  HU-06 Unhappy: GET /readings/latest sin datos → 404
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.posture_capture.application.commands.save_reading_handler import SaveReadingHandler
from src.posture_capture.application.queries.get_latest_reading_handler import GetLatestReadingHandler
from src.posture_capture.domain.entities.posture_reading import PostureReading
from src.posture_capture.domain.value_objects.sensor_data import SensorData
from src.posture_capture.interfaces.rest import readings_router
from uuid import uuid4
from datetime import datetime, timezone

VALID_PAYLOAD = {
    "vest_id": "vest-001",
    "cervical": [0.1, 0.2, 9.8],
    "dorsal":   [0.05, 0.1, 9.9],
    "lumbar":   [0.0, 0.15, 9.7],
}


class _InMemoryRepo:
    def __init__(self) -> None:
        self.saved: list[PostureReading] = []

    async def save(self, reading: PostureReading) -> None:
        self.saved.append(reading)

    async def find_latest(self) -> PostureReading | None:
        return self.saved[-1] if self.saved else None


class _StubMLClient:
    async def classify(self, reading: PostureReading) -> tuple[str, float]:
        return "adequate", 0.95


@pytest.fixture
def client_and_repo():
    repo = _InMemoryRepo()
    handler = SaveReadingHandler(repo, _StubMLClient())
    latest_handler = GetLatestReadingHandler(repo)
    app.dependency_overrides[readings_router.get_handler] = lambda: handler
    app.dependency_overrides[readings_router.get_latest_handler] = lambda: latest_handler
    with TestClient(app) as c:
        yield c, repo
    app.dependency_overrides.clear()


# ── HU-01 ──────────────────────────────────────────────────────────────────────

# Happy: chaleco envía battery_percent → se almacena correctamente
def test_hu01_battery_percent_almacenado(client_and_repo):
    client, repo = client_and_repo
    payload = {**VALID_PAYLOAD, "battery_percent": 72}
    response = client.post("/api/v1/readings", json=payload)
    assert response.status_code == 201
    assert repo.saved[0].battery_percent == 72


# Unhappy: chaleco no envía battery_percent → se usa default 100
def test_hu01_battery_default_cuando_no_se_envia(client_and_repo):
    client, repo = client_and_repo
    response = client.post("/api/v1/readings", json=VALID_PAYLOAD)
    assert response.status_code == 201
    assert repo.saved[0].battery_percent == 100


# ── HU-02 ──────────────────────────────────────────────────────────────────────

# Happy: JSON válido → 201, almacenado con clase postural
def test_hu02_almacenamiento_exitoso(client_and_repo):
    client, repo = client_and_repo
    response = client.post("/api/v1/readings", json=VALID_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["posture_class"] == "adequate"
    assert body["confidence"] == 0.95
    assert "id" in body
    assert len(repo.saved) == 1


# Unhappy: falta campo dorsal → 422, no almacenado
def test_hu02_datos_incompletos_no_almacenados(client_and_repo):
    client, repo = client_and_repo
    payload = {k: v for k, v in VALID_PAYLOAD.items() if k != "dorsal"}
    response = client.post("/api/v1/readings", json=payload)
    assert response.status_code == 422
    assert len(repo.saved) == 0


# ── HU-03 ──────────────────────────────────────────────────────────────────────

# Happy: valores dentro de ±16g → aceptados
def test_hu03_datos_en_rango_valido_aceptados(client_and_repo):
    client, repo = client_and_repo
    payload = {**VALID_PAYLOAD, "dorsal": [0.0, 0.0, 9.81]}
    response = client.post("/api/v1/readings", json=payload)
    assert response.status_code == 201
    assert len(repo.saved) == 1


# Unhappy: valor fuera de ±16g → 400, no almacenado
def test_hu03_datos_fuera_de_rango_retornan_400(client_and_repo):
    client, repo = client_and_repo
    payload = {**VALID_PAYLOAD, "dorsal": [0.0, 0.0, 20.0]}
    response = client.post("/api/v1/readings", json=payload)
    assert response.status_code == 400
    assert "rango" in response.json()["detail"].lower()
    assert len(repo.saved) == 0


# ── HU-06 ──────────────────────────────────────────────────────────────────────

# Happy: hay lecturas → GET /latest devuelve la más reciente
def test_hu06_latest_devuelve_ultima_lectura(client_and_repo):
    client, repo = client_and_repo
    client.post("/api/v1/readings", json={**VALID_PAYLOAD, "battery_percent": 80})
    response = client.get("/api/v1/readings/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["posture_class"] == "adequate"
    assert body["vest_id"] == "vest-001"
    assert body["battery_percent"] == 80
    assert "timestamp" in body


# Unhappy: sin lecturas previas → 404
def test_hu06_latest_sin_datos_retorna_404(client_and_repo):
    client, repo = client_and_repo
    response = client.get("/api/v1/readings/latest")
    assert response.status_code == 404
