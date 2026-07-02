from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.iam.application.internal.commandservices.user_command_service import (
    UserCommandService,
    _hash_token,
)
from src.iam.domain.entities.password_reset_token import PasswordResetToken
from src.iam.domain.entities.user import User
from src.iam.domain.model.commands.request_password_reset_command import (
    RequestPasswordResetCommand,
)
from src.iam.domain.model.commands.reset_password_command import (
    InvalidResetTokenError,
    ResetPasswordCommand,
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


class _ResetRepo:
    def __init__(self):
        self.tokens = []
    async def save(self, t):
        self.tokens.append(t)
    async def find_by_hash(self, h):
        return next((t for t in self.tokens if t.token_hash == h), None)
    async def invalidate_for_user(self, user_id):
        self.tokens = [t for t in self.tokens if t.user_id != user_id]
    async def mark_used(self, token_id, used_at):
        for t in self.tokens:
            if t.id == token_id:
                t.used_at = used_at


class _Email:
    def __init__(self):
        self.sent = []
    async def send_password_reset(self, to_email, to_name, reset_link):
        self.sent.append((to_email, to_name, reset_link))


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
    reset_repo = _ResetRepo()
    email = _Email()
    svc = UserCommandService(
        user_repository=user_repo,
        notification_repository=None,
        password_service=_Passwords(),
        token_service=None,
        reset_token_repository=reset_repo,
        email_service=email,
        app_base_url="https://app.test",
        reset_token_ttl_seconds=3600,
    )
    return svc, user_repo, reset_repo, email


# ── forgot-password ──────────────────────────────────────────────────────────

async def test_forgot_correo_existente_guarda_token_hasheado_y_envia_enlace():
    user = _user()
    svc, _ur, reset_repo, email = _service([user])
    await svc.handle_request_password_reset(RequestPasswordResetCommand(email="ana@correo.com"))
    assert len(reset_repo.tokens) == 1
    saved = reset_repo.tokens[0]
    # En la BD solo hay hash, nunca el crudo.
    assert saved.token_hash != ""
    assert len(email.sent) == 1
    _to, _name, link = email.sent[0]
    assert link.startswith("https://app.test/reset-password?token=")
    raw = link.split("token=")[1]
    assert _hash_token(raw) == saved.token_hash  # el crudo del enlace hashea al guardado


async def test_forgot_correo_inexistente_no_crea_token_ni_envia():
    svc, _ur, reset_repo, email = _service([])
    await svc.handle_request_password_reset(RequestPasswordResetCommand(email="nadie@correo.com"))
    assert reset_repo.tokens == []
    assert email.sent == []


async def test_forgot_invalida_tokens_previos_del_usuario():
    user = _user()
    svc, _ur, reset_repo, _email = _service([user])
    await svc.handle_request_password_reset(RequestPasswordResetCommand(email="ana@correo.com"))
    await svc.handle_request_password_reset(RequestPasswordResetCommand(email="ana@correo.com"))
    assert len(reset_repo.tokens) == 1  # el primero se invalidó


# ── reset-password ───────────────────────────────────────────────────────────

async def test_reset_token_valido_cambia_la_contrasena():
    user = _user()
    svc, user_repo, reset_repo, _email = _service([user])
    raw = "token-crudo-de-prueba"
    reset_repo.tokens.append(PasswordResetToken(
        id=uuid4(), user_id=user.id, token_hash=_hash_token(raw),
        expires_at=NOW + timedelta(hours=999999), created_at=NOW,
    ))
    await svc.handle_reset_password(ResetPasswordCommand(token=raw, new_password="NuevaClave1"))
    assert (await user_repo.find_by_id(user.id)).password_hash == "hashed:NuevaClave1"


async def test_reset_token_de_un_solo_uso():
    user = _user()
    svc, _ur, reset_repo, _email = _service([user])
    raw = "token-crudo"
    reset_repo.tokens.append(PasswordResetToken(
        id=uuid4(), user_id=user.id, token_hash=_hash_token(raw),
        expires_at=NOW + timedelta(hours=999999), created_at=NOW,
    ))
    await svc.handle_reset_password(ResetPasswordCommand(token=raw, new_password="NuevaClave1"))
    with pytest.raises(InvalidResetTokenError):
        await svc.handle_reset_password(ResetPasswordCommand(token=raw, new_password="OtraClave2"))


async def test_reset_token_vencido_falla():
    user = _user()
    svc, _ur, reset_repo, _email = _service([user])
    raw = "token-vencido"
    reset_repo.tokens.append(PasswordResetToken(
        id=uuid4(), user_id=user.id, token_hash=_hash_token(raw),
        expires_at=datetime.utcnow() - timedelta(seconds=1), created_at=NOW,
    ))
    with pytest.raises(InvalidResetTokenError):
        await svc.handle_reset_password(ResetPasswordCommand(token=raw, new_password="NuevaClave1"))


async def test_reset_token_inexistente_falla():
    svc, _ur, _rr, _email = _service([_user()])
    with pytest.raises(InvalidResetTokenError):
        await svc.handle_reset_password(ResetPasswordCommand(token="no-existe", new_password="NuevaClave1"))


async def test_reset_contrasena_corta_falla():
    user = _user()
    svc, _ur, reset_repo, _email = _service([user])
    raw = "token-ok"
    reset_repo.tokens.append(PasswordResetToken(
        id=uuid4(), user_id=user.id, token_hash=_hash_token(raw),
        expires_at=NOW + timedelta(hours=999999), created_at=NOW,
    ))
    with pytest.raises(ValueError):
        await svc.handle_reset_password(ResetPasswordCommand(token=raw, new_password="corta"))
