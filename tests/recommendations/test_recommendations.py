"""
Tests Gherkin HU-10:
  Escenario 1: Recomendaciones para encorvamiento frontal
  Escenario 2: Recomendaciones para reclinación excesiva
  Extra: clase inválida → 400
"""
import pytest
from fastapi.testclient import TestClient

from src.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# HU-10 Escenario 1 — Recomendaciones encorvamiento frontal
def test_recomendaciones_forward_slouch(client):
    response = client.get("/api/v1/recommendations/forward_slouch")
    assert response.status_code == 200
    recs = response.json()
    assert len(recs) >= 1
    titles = [r["title"].lower() for r in recs]
    assert any("monitor" in t for t in titles), "Debe incluir ajuste de monitor"
    for r in recs:
        assert "title" in r and "description" in r


# HU-10 Escenario 2 — Recomendaciones reclinación excesiva
def test_recomendaciones_excessive_recline(client):
    response = client.get("/api/v1/recommendations/excessive_recline")
    assert response.status_code == 200
    recs = response.json()
    assert len(recs) >= 1
    titles = [r["title"].lower() for r in recs]
    assert any("respaldo" in t for t in titles), "Debe incluir ajuste de respaldo"


# Clase válida — postura adecuada también tiene recomendaciones
def test_recomendaciones_adequate(client):
    response = client.get("/api/v1/recommendations/adequate")
    assert response.status_code == 200
    assert len(response.json()) >= 1


# Clase inválida → 400
def test_clase_invalida_retorna_400(client):
    response = client.get("/api/v1/recommendations/invalid_class")
    assert response.status_code == 400
    assert "inválida" in response.json()["detail"].lower()
