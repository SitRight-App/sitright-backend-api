from datetime import datetime
from uuid import uuid4

import pytest

from src.iam.application.internal.commandservices.user_command_service import (
    UserCommandService,
)
from src.iam.domain.entities.user import User
from src.iam.domain.model.commands.change_password_command import (
    ChangePasswordCommand,
    InvalidCurrentPasswordError,
)
from src.iam.domain.value_objects.role import Role

NOW = datetime(2026, 7, 1, 12, 0, 0)


class _UserRepo:
    def __init__(self, users):
        self._by_id = {u.id: u for u in users}
    async def find_by_email(self, email):
        e = email.lower().strip()
        return next((u for u in self._by_id.values() if u.email == e), None)
    async def find_by_id(self, uid):
        return self._by_id.get(uid)
    async def save(self, user):
        self._by_id[user.id] = user


class _Email:
    def __init__(self):
        self.sent = []
        self.password_changed_sent = []
    async def send_password_reset(self, to_email, to_name, reset_link):
        self.sent.append((to_email, to_name, reset_link))
    async def send_password_changed(self, to_email, to_name):
        self.password_changed_sent.append((to_email, to_name))


class _Passwords:
    def hash(self, plain):
        return f"hashed:{plain}"
    def verify(self, plain, hashed):
        return hashed == f"hashed:{plain}"


def _user(**kw) -> User:
    base = dict(
        id=uuid4(), name="Ana", email="ana@correo.com", password_hash="hashed:old",
        role=Role.WORKER, created_at=NOW, updated_at=NOW, is_active=True,
    )
    base.update(kw)
    return User(**base)


def _service(users):
    user_repo = _UserRepo(users)
    email = _Email()
    svc = UserCommandService(
        user_repository=user_repo,
        notification_repository=None,
        password_service=_Passwords(),
        token_service=None,
        reset_token_repository=None,
        email_service=email,
        app_base_url="https://app.test",
        reset_token_ttl_seconds=3600,
    )
    return svc, user_repo, email


# ── change-password ──────────────────────────────────────────────────────────

async def test_cambio_exitoso_envia_correo_de_aviso_y_actualiza_hash():
    user = _user()
    svc, user_repo, email = _service([user])
    await svc.handle_change_password(
        ChangePasswordCommand(user_id=user.id, current_password="old", new_password="NuevaClave1")
    )
    assert (await user_repo.find_by_id(user.id)).password_hash == "hashed:NuevaClave1"
    assert email.password_changed_sent == [(user.email, user.name)]


async def test_contrasena_actual_incorrecta_falla_y_no_envia_correo():
    user = _user()
    svc, user_repo, email = _service([user])
    with pytest.raises(InvalidCurrentPasswordError):
        await svc.handle_change_password(
            ChangePasswordCommand(user_id=user.id, current_password="mala", new_password="NuevaClave1")
        )
    assert (await user_repo.find_by_id(user.id)).password_hash == "hashed:old"
    assert email.password_changed_sent == []
