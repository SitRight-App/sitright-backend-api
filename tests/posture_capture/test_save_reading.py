"""
Tests de criterios de aceptación:
  HU-01 Happy : POST /readings con battery_percent → 201, battery almacenada
  HU-01 Unhappy: POST sin battery_percent → usa default 100%, igual 201
  HU-02 Happy : JSON válido con 3 sensores → 201, almacenado en repo
  HU-02 Unhappy: campo faltante → 422, no almacenado
  HU-03 Happy : valores dentro de ±16g → 201
  HU-03 Unhappy: valor fuera de ±16g → 400, no almacenado
  HU-06 Happy : GET /readings/latest → devuelve última lectura del chaleco del usuario
  HU-06 Unhappy: GET /readings/latest sin datos → 404
  HU-06 Unhappy: GET /readings/latest sin chaleco vinculado → 404
"""
import pytest
from fastapi.testclient import TestClient

from src.iam.domain.services.token_service import TokenPayload
from src.iam.domain.value_objects.role import Role
from src.iam.interfaces.rest.dependencies import get_current_user
from src.main import app
from src.posture_capture.application.commands.save_reading_handler import SaveReadingHandler
from src.posture_capture.application.queries.get_latest_reading_handler import GetLatestReadingHandler
from src.posture_capture.domain.entities.posture_reading import PostureReading
from src.posture_capture.interfaces.rest import readings_router
from src.vest_management.application.queries.get_my_vest_handler import GetMyVestHandler
from src.vest_management.application.queries.get_vest_by_mac_handler import (
    GetVestByMacHandler,
)
from src.vest_management.domain.entities.vest_device import VestDevice
from uuid import UUID, uuid4
from datetime import datetime, timezone

USER_ID = uuid4()
VEST_ID = uuid4()
VEST_MAC = "AA:BB:CC:11:22:33"

# El firmware envía la MAC del chaleco en el campo "vest_id" del payload;
# el backend la resuelve contra el repositorio de vest_management.
VALID_PAYLOAD = {
    "vest_id": VEST_MAC,
    "cervical": [0.1, 0.2, 9.8],
    "dorsal":   [0.05, 0.1, 9.9],
    "lumbar":   [0.0, 0.15, 9.7],
}


class _InMemoryRepo:
    def __init__(self) -> None:
        self.saved: list[PostureReading] = []

    async def save(self, reading: PostureReading) -> None:
        self.saved.append(reading)

    async def find_latest(self, vest_id: str | None = None) -> PostureReading | None:
        items = [r for r in self.saved if vest_id is None or r.vest_id == vest_id]
        return items[-1] if items else None

    async def find_recent(self, *, vest_id=None, limit=60, since=None, until=None):
        items = [r for r in self.saved if vest_id is None or r.vest_id == vest_id]
        return items[-limit:]


class _StubMLClient:
    async def classify(self, reading: PostureReading) -> tuple[str, float]:
        return "adequate", 0.95


class _StubVestRepo:
    """Repo en memoria mínimo: responde find_by_user_id y find_by_mac_address."""

    def __init__(self, vest: VestDevice | None) -> None:
        self._vest = vest

    async def find_by_user_id(self, user_id: UUID) -> VestDevice | None:
        if self._vest is None:
            return None
        return self._vest if self._vest.user_id == user_id else None

    async def find_by_mac_address(self, mac: str) -> VestDevice | None:
        if self._vest is None:
            return None
        return self._vest if self._vest.mac_address == mac else None

    # Métodos no usados en estos tests, pero presentes en el Protocol.
    async def save(self, device): ...  # pragma: no cover
    async def find_by_id(self, device_id): ...  # pragma: no cover
    async def find_by_mqtt_username(self, username): ...  # pragma: no cover
    async def exists_by_mac_address(self, mac): return False  # pragma: no cover


def _build_linked_vest() -> VestDevice:
    return VestDevice(
        id=VEST_ID,
        mac_address=VEST_MAC,
        firmware_version="1.0.0",
        created_at=datetime.now(timezone.utc),
        user_id=USER_ID,
        linked_at=datetime.now(timezone.utc),
        is_active=True,
    )


def _build_unlinked_vest() -> VestDevice:
    """Chaleco registrado pero sin user_id (no vinculado)."""
    return VestDevice(
        id=VEST_ID,
        mac_address=VEST_MAC,
        firmware_version="1.0.0",
        created_at=datetime.now(timezone.utc),
        user_id=None,
        linked_at=None,
        is_active=False,
    )


def _fake_current_user() -> TokenPayload:
    return TokenPayload(user_id=USER_ID, email="t@t.com", role=Role.WORKER, type="access")


@pytest.fixture
def client_and_repo():
    repo = _InMemoryRepo()
    handler = SaveReadingHandler(repo, _StubMLClient())
    latest_handler = GetLatestReadingHandler(repo)
    vest_repo = _StubVestRepo(_build_linked_vest())
    vest_handler = GetMyVestHandler(vest_repo)
    vest_by_mac_handler = GetVestByMacHandler(vest_repo)
    app.dependency_overrides[readings_router.get_handler] = lambda: handler
    app.dependency_overrides[readings_router.get_latest_handler] = lambda: latest_handler
    app.dependency_overrides[readings_router.get_my_vest_handler] = lambda: vest_handler
    app.dependency_overrides[readings_router.get_vest_by_mac_handler] = (
        lambda: vest_by_mac_handler
    )
    app.dependency_overrides[get_current_user] = _fake_current_user
    with TestClient(app) as c:
        yield c, repo
    app.dependency_overrides.clear()


@pytest.fixture
def client_without_vest():
    """Cliente cuyo usuario NO tiene chaleco vinculado — para probar el 404."""
    repo = _InMemoryRepo()
    handler = SaveReadingHandler(repo, _StubMLClient())
    latest_handler = GetLatestReadingHandler(repo)
    vest_repo = _StubVestRepo(None)
    vest_handler = GetMyVestHandler(vest_repo)
    vest_by_mac_handler = GetVestByMacHandler(vest_repo)
    app.dependency_overrides[readings_router.get_handler] = lambda: handler
    app.dependency_overrides[readings_router.get_latest_handler] = lambda: latest_handler
    app.dependency_overrides[readings_router.get_my_vest_handler] = lambda: vest_handler
    app.dependency_overrides[readings_router.get_vest_by_mac_handler] = (
        lambda: vest_by_mac_handler
    )
    app.dependency_overrides[get_current_user] = _fake_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_unlinked_vest():
    """Chaleco existe en BD pero sin user_id — para probar HU-02 AC3 (403)."""
    repo = _InMemoryRepo()
    handler = SaveReadingHandler(repo, _StubMLClient())
    vest_repo = _StubVestRepo(_build_unlinked_vest())
    vest_by_mac_handler = GetVestByMacHandler(vest_repo)
    app.dependency_overrides[readings_router.get_handler] = lambda: handler
    app.dependency_overrides[readings_router.get_vest_by_mac_handler] = (
        lambda: vest_by_mac_handler
    )
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


# Unhappy HU-02 AC3: el chaleco no está vinculado a ningún usuario → 403 + log
def test_hu02_chaleco_no_vinculado_retorna_403(client_with_unlinked_vest, caplog):
    client, repo = client_with_unlinked_vest
    import logging
    with caplog.at_level(logging.WARNING):
        response = client.post("/api/v1/readings", json=VALID_PAYLOAD)
    assert response.status_code == 403
    assert "vinculado" in response.json()["detail"].lower()
    assert len(repo.saved) == 0
    # Log del intento (AC3 lo exige)
    assert any("no vinculado" in r.message.lower() for r in caplog.records)


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

# Happy: hay lecturas para el chaleco del usuario → GET /latest devuelve la más reciente
def test_hu06_latest_devuelve_ultima_lectura(client_and_repo):
    client, repo = client_and_repo
    client.post("/api/v1/readings", json={**VALID_PAYLOAD, "battery_percent": 80})
    response = client.get("/api/v1/readings/latest")
    assert response.status_code == 200
    body = response.json()
    assert body["posture_class"] == "adequate"
    assert body["vest_id"] == VEST_MAC
    assert body["battery_percent"] == 80
    assert "timestamp" in body


# Unhappy: usuario tiene chaleco pero sin lecturas previas → 404
def test_hu06_latest_sin_datos_retorna_404(client_and_repo):
    client, _repo = client_and_repo
    response = client.get("/api/v1/readings/latest")
    assert response.status_code == 404
    assert "lecturas" in response.json()["detail"].lower()


# Unhappy: usuario NO tiene chaleco vinculado → 404 (no leak)
def test_hu06_latest_sin_chaleco_vinculado_retorna_404(client_without_vest):
    client = client_without_vest
    response = client.get("/api/v1/readings/latest")
    assert response.status_code == 404
    assert "chaleco" in response.json()["detail"].lower()


# Unhappy: lectura de otro chaleco NO se filtra al usuario actual
def test_hu06_latest_no_devuelve_lectura_de_otro_chaleco(client_and_repo):
    client, _repo = client_and_repo
    # Lectura de un chaleco ajeno
    other_payload = {**VALID_PAYLOAD, "vest_id": str(uuid4()), "battery_percent": 50}
    client.post("/api/v1/readings", json=other_payload)
    response = client.get("/api/v1/readings/latest")
    assert response.status_code == 404, (
        "El usuario no debería ver lecturas de chalecos que no le pertenecen"
    )
