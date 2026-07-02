import pytest
from fastapi.testclient import TestClient

from src.iam.domain.model.commands.reset_password_command import (
    InvalidResetTokenError,
    ResetPasswordCommand,
)
from src.iam.interfaces.rest import auth_router
from src.main import app


class _CmdServiceOK:
    def __init__(self):
        self.calls = []
    async def handle_reset_password(self, command: ResetPasswordCommand) -> None:
        self.calls.append(command)


class _CmdServiceInvalid:
    async def handle_reset_password(self, command: ResetPasswordCommand) -> None:
        raise InvalidResetTokenError("El enlace no es válido o expiró")


# Nota: se usa TestClient(app) SIN context manager a propósito. El `with`
# dispararía el lifespan (seed_demo_users -> MongoDB); sin él, no se conecta a
# Mongo y el override del command service resuelve el endpoint igual.
@pytest.fixture
def client_ok():
    svc = _CmdServiceOK()
    app.dependency_overrides[auth_router.get_user_command_service] = lambda: svc
    yield TestClient(app), svc
    app.dependency_overrides.clear()


@pytest.fixture
def client_invalid():
    app.dependency_overrides[auth_router.get_user_command_service] = lambda: _CmdServiceInvalid()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_reset_exitoso_devuelve_204(client_ok):
    client, svc = client_ok
    r = client.post("/api/v1/auth/reset-password", json={"token": "abc", "new_password": "NuevaClave1"})
    assert r.status_code == 204
    assert svc.calls[0].token == "abc"
    assert svc.calls[0].new_password == "NuevaClave1"


def test_reset_token_invalido_devuelve_400(client_invalid):
    r = client_invalid.post("/api/v1/auth/reset-password", json={"token": "malo", "new_password": "NuevaClave1"})
    assert r.status_code == 400
    assert "válido" in r.json()["detail"].lower() or "expir" in r.json()["detail"].lower()


def test_reset_contrasena_corta_devuelve_422(client_invalid):
    r = client_invalid.post("/api/v1/auth/reset-password", json={"token": "abc", "new_password": "corta"})
    assert r.status_code == 422
