from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.iam.domain.services.token_service import TokenPayload
from src.iam.domain.value_objects.role import Role
from src.iam.interfaces.rest.dependencies import require_admin
from src.main import app
from src.training_data.interfaces.rest import training_router

SAMPLE = {
    "subject": "s1",
    "label": "adequate",
    "cervical": [0, 0, 1],
    "dorsal": [0, 0, 1],
    "lumbar": [0, 0, 1],
}


class _InMemoryRepo:
    def __init__(self) -> None:
        self.saved: list = []

    async def save_many(self, samples) -> None:
        self.saved.extend(samples)

    async def list_all(self):
        return list(self.saved)

    async def counts(self) -> dict:
        by_label: dict[str, int] = {}
        by_subject: dict[str, int] = {}
        for s in self.saved:
            by_label[s.label] = by_label.get(s.label, 0) + 1
            by_subject[s.subject] = by_subject.get(s.subject, 0) + 1
        return {"total": len(self.saved), "by_label": by_label, "by_subject": by_subject}


def _fake_admin() -> TokenPayload:
    return TokenPayload(user_id=uuid4(), role=Role.ADMIN, type="access")


@pytest.fixture
def client_and_repo():
    repo = _InMemoryRepo()
    training_router.set_repository(repo)
    app.dependency_overrides[require_admin] = _fake_admin
    yield TestClient(app), repo
    app.dependency_overrides.clear()


def test_guardar_muestras(client_and_repo):
    client, repo = client_and_repo
    body = {"samples": [SAMPLE, {**SAMPLE, "label": "forward_slouch"}]}
    r = client.post("/api/v1/training/samples", json=body)
    assert r.status_code == 201
    assert r.json()["saved"] == 2
    assert len(repo.saved) == 2


def test_etiqueta_invalida_da_400(client_and_repo):
    client, _ = client_and_repo
    r = client.post("/api/v1/training/samples", json={"samples": [{**SAMPLE, "label": "foo"}]})
    assert r.status_code == 400


def test_stats_cuenta_por_clase(client_and_repo):
    client, _ = client_and_repo
    client.post(
        "/api/v1/training/samples",
        json={"samples": [SAMPLE, SAMPLE, {**SAMPLE, "label": "forward_slouch"}]},
    )
    body = client.get("/api/v1/training/samples/stats").json()
    assert body["total"] == 3
    assert body["by_label"]["adequate"] == 2


def test_export_csv(client_and_repo):
    client, _ = client_and_repo
    client.post("/api/v1/training/samples", json={"samples": [SAMPLE]})
    r = client.get("/api/v1/training/samples/export")
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "cervical_ax" in r.text and "s1" in r.text
