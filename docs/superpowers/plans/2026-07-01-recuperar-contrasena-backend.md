# Recuperar contraseña — Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Completar en el backend el flujo de recuperación de contraseña: generar un token de reset (hasheado, un solo uso, TTL 1h), enviarlo por correo con Brevo (con modo dev), y exponer `POST /auth/reset-password` para fijar la nueva contraseña.

**Architecture:** Bounded context `iam` en capas DDD. Dominio nuevo (entidad `PasswordResetToken`, interfaces `PasswordResetTokenRepository` y `EmailService`, comando `ResetPasswordCommand`). Aplicación (`UserCommandService`) implementa los dos casos de uso. Infraestructura implementa el repo Mongo y el email Brevo (SMTP). Interfaces REST agregan el endpoint. Dominio y aplicación NO importan `motor`/`pymongo`/`smtplib`.

**Tech Stack:** FastAPI, Motor (MongoDB async), Pydantic v2, `smtplib` (stdlib) sobre Brevo SMTP, pytest + pytest-asyncio (`asyncio_mode=auto`).

## Global Constraints

- Dominio y aplicación solo importan stdlib + el propio dominio. `motor`/`smtplib` solo en `infrastructure/`.
- Fechas: **UTC naive** (`datetime.utcnow()`), consistente con el código existente (p. ej. `handle_change_password`).
- Token: se envía el crudo en el enlace; en Mongo se guarda **solo** `sha256(crudo)`. Un solo uso; al pedir uno nuevo se invalidan los previos del usuario; TTL 1h.
- Respuestas sin enumeración de cuentas: `POST /auth/forgot-password` sigue devolviendo `202` uniforme; `POST /auth/reset-password` devuelve `204` en éxito y `400` genérico ("El enlace no es válido o expiró") en token inválido/expirado/usado o contraseña corta.
- Enlace del correo: `{settings.app_base_url}/reset-password?token=<crudo>`.
- Modo dev: si faltan credenciales SMTP de Brevo, no se envía correo y se **loguea el enlace**.
- Tests en `tests/iam/`. Commits con `git` normal (identidad del repo: `Christopher <79271081+ChrisByBits@users.noreply.github.com>`), sin atribución a Claude.

## File Structure

| Archivo | Responsabilidad |
|---|---|
| `src/iam/domain/entities/password_reset_token.py` | Entidad + `is_valid(now)` |
| `src/iam/domain/repositories/password_reset_token_repository.py` | Interfaz repo (Protocol) |
| `src/iam/domain/services/email_service.py` | Interfaz email (Protocol) |
| `src/iam/domain/model/commands/reset_password_command.py` | `ResetPasswordCommand` + `InvalidResetTokenError` |
| `src/iam/infrastructure/persistence/mongo_password_reset_token_repository.py` | Impl Mongo + `ensure_indexes` |
| `src/iam/infrastructure/email/__init__.py` | paquete nuevo |
| `src/iam/infrastructure/email/brevo_email_service.py` | Impl email Brevo SMTP + modo dev |
| `src/iam/domain/services/user_command_service.py` | + `handle_reset_password` en la interfaz |
| `src/iam/application/internal/commandservices/user_command_service.py` | 2 handlers + deps nuevas |
| `src/shared/config.py` | variables de entorno nuevas |
| `src/main.py` | wiring (repo + email + índices) |
| `src/iam/interfaces/schemas/auth_schema.py` | `ResetPasswordRequest` |
| `src/iam/interfaces/rest/auth_router.py` | endpoint `POST /auth/reset-password` |
| `tests/iam/__init__.py`, `tests/iam/test_*.py` | tests |

---

### Task 1: Dominio — entidad, interfaces y comando

**Files:**
- Create: `src/iam/domain/entities/password_reset_token.py`
- Create: `src/iam/domain/repositories/password_reset_token_repository.py`
- Create: `src/iam/domain/services/email_service.py`
- Create: `src/iam/domain/model/commands/reset_password_command.py`
- Create: `tests/iam/__init__.py` (vacío)
- Test: `tests/iam/test_password_reset_token_entity.py`

**Interfaces:**
- Produces:
  - `PasswordResetToken(id: UUID, user_id: UUID, token_hash: str, expires_at: datetime, created_at: datetime, used_at: datetime | None = None)` con `is_valid(now: datetime) -> bool`.
  - `PasswordResetTokenRepository` (Protocol): `save(token)`, `find_by_hash(token_hash) -> PasswordResetToken | None`, `invalidate_for_user(user_id)`, `mark_used(token_id, used_at)`.
  - `EmailService` (Protocol): `send_password_reset(to_email, to_name, reset_link)`.
  - `ResetPasswordCommand(token: str, new_password: str)` (frozen) + `InvalidResetTokenError(Exception)`.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/iam/__init__.py` vacío y `tests/iam/test_password_reset_token_entity.py`:

```python
from datetime import datetime, timedelta
from uuid import uuid4

from src.iam.domain.entities.password_reset_token import PasswordResetToken

NOW = datetime(2026, 7, 1, 12, 0, 0)


def _token(**kw) -> PasswordResetToken:
    base = dict(
        id=uuid4(),
        user_id=uuid4(),
        token_hash="hash",
        expires_at=NOW + timedelta(hours=1),
        created_at=NOW,
        used_at=None,
    )
    base.update(kw)
    return PasswordResetToken(**base)


def test_valido_cuando_no_usado_y_no_vencido():
    assert _token().is_valid(NOW) is True


def test_invalido_cuando_vencido():
    assert _token(expires_at=NOW - timedelta(seconds=1)).is_valid(NOW) is False


def test_invalido_cuando_ya_usado():
    assert _token(used_at=NOW).is_valid(NOW) is False
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/iam/test_password_reset_token_entity.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'src.iam.domain.entities.password_reset_token'`.

- [ ] **Step 3: Implementar el dominio**

`src/iam/domain/entities/password_reset_token.py`:

```python
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class PasswordResetToken:
    """HU-27 — token de recuperación. En Mongo se guarda solo el hash; el crudo
    viaja en el enlace del correo. Un solo uso, con caducidad (TTL 1h)."""

    id: UUID
    user_id: UUID
    token_hash: str
    expires_at: datetime
    created_at: datetime
    used_at: datetime | None = None

    def is_valid(self, now: datetime) -> bool:
        return self.used_at is None and now < self.expires_at
```

`src/iam/domain/repositories/password_reset_token_repository.py`:

```python
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..entities.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository(Protocol):
    async def save(self, token: PasswordResetToken) -> None: ...
    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None: ...
    async def invalidate_for_user(self, user_id: UUID) -> None: ...
    async def mark_used(self, token_id: UUID, used_at: datetime) -> None: ...
```

`src/iam/domain/services/email_service.py`:

```python
from typing import Protocol


class EmailService(Protocol):
    async def send_password_reset(
        self, to_email: str, to_name: str, reset_link: str
    ) -> None: ...
```

`src/iam/domain/model/commands/reset_password_command.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ResetPasswordCommand:
    token: str
    new_password: str


class InvalidResetTokenError(Exception):
    """HU-27 — el token de recuperación es inválido, expiró o ya se usó."""
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python -m pytest tests/iam/test_password_reset_token_entity.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/iam/domain/entities/password_reset_token.py \
        src/iam/domain/repositories/password_reset_token_repository.py \
        src/iam/domain/services/email_service.py \
        src/iam/domain/model/commands/reset_password_command.py \
        tests/iam/__init__.py tests/iam/test_password_reset_token_entity.py
git commit -m "feat(iam): dominio de recuperacion de contrasena (token, repo, email, comando)"
```

---

### Task 2: Infraestructura — repositorio Mongo del token

**Files:**
- Create: `src/iam/infrastructure/persistence/mongo_password_reset_token_repository.py`
- Test: `tests/iam/test_mongo_reset_token_repo.py`

**Interfaces:**
- Consumes: `PasswordResetToken` (Task 1).
- Produces: `MongoPasswordResetTokenRepository(db)` que cumple `PasswordResetTokenRepository`, más `ensure_indexes()` (índice único en `token_hash` + índice TTL en `expires_at`). Métodos puros `_to_document` / `_from_document`.

Nota: `expires_at` se guarda como `datetime` (BSON Date) para que funcione el índice TTL; `created_at`/`used_at` como ISO string (consistente con `MongoUserRepository`). El test valida el round-trip de mapeo sin necesidad de Mongo.

- [ ] **Step 1: Escribir el test que falla**

`tests/iam/test_mongo_reset_token_repo.py`:

```python
from datetime import datetime, timedelta
from uuid import uuid4

from src.iam.domain.entities.password_reset_token import PasswordResetToken
from src.iam.infrastructure.persistence.mongo_password_reset_token_repository import (
    MongoPasswordResetTokenRepository,
)

NOW = datetime(2026, 7, 1, 12, 0, 0)


def _repo() -> MongoPasswordResetTokenRepository:
    # Instancia sin __init__ para probar solo el mapeo (no toca Mongo).
    return MongoPasswordResetTokenRepository.__new__(MongoPasswordResetTokenRepository)


def test_roundtrip_documento_sin_usar():
    t = PasswordResetToken(
        id=uuid4(), user_id=uuid4(), token_hash="abc123",
        expires_at=NOW + timedelta(hours=1), created_at=NOW, used_at=None,
    )
    repo = _repo()
    assert repo._from_document(repo._to_document(t)) == t


def test_roundtrip_documento_usado():
    t = PasswordResetToken(
        id=uuid4(), user_id=uuid4(), token_hash="abc123",
        expires_at=NOW + timedelta(hours=1), created_at=NOW, used_at=NOW,
    )
    repo = _repo()
    assert repo._from_document(repo._to_document(t)) == t


def test_expires_at_se_guarda_como_datetime_para_el_indice_ttl():
    t = PasswordResetToken(
        id=uuid4(), user_id=uuid4(), token_hash="abc123",
        expires_at=NOW + timedelta(hours=1), created_at=NOW, used_at=None,
    )
    doc = _repo()._to_document(t)
    assert isinstance(doc["expires_at"], datetime)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/iam/test_mongo_reset_token_repo.py -v`
Expected: FAIL con `ModuleNotFoundError` del repo.

- [ ] **Step 3: Implementar el repositorio Mongo**

`src/iam/infrastructure/persistence/mongo_password_reset_token_repository.py`:

```python
from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...domain.entities.password_reset_token import PasswordResetToken


def _as_dt(value) -> datetime:
    return value if isinstance(value, datetime) else datetime.fromisoformat(value)


class MongoPasswordResetTokenRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["password_reset_tokens"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("token_hash", unique=True)
        # Mongo purga automáticamente los documentos vencidos.
        await self._col.create_index("expires_at", expireAfterSeconds=0)

    async def save(self, token: PasswordResetToken) -> None:
        await self._col.replace_one(
            {"_id": str(token.id)}, self._to_document(token), upsert=True
        )

    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        doc = await self._col.find_one({"token_hash": token_hash})
        return self._from_document(doc) if doc else None

    async def invalidate_for_user(self, user_id: UUID) -> None:
        await self._col.delete_many({"user_id": str(user_id)})

    async def mark_used(self, token_id: UUID, used_at: datetime) -> None:
        await self._col.update_one(
            {"_id": str(token_id)}, {"$set": {"used_at": used_at.isoformat()}}
        )

    def _to_document(self, t: PasswordResetToken) -> dict:
        return {
            "_id": str(t.id),
            "user_id": str(t.user_id),
            "token_hash": t.token_hash,
            "expires_at": t.expires_at,  # BSON Date (para el índice TTL)
            "created_at": t.created_at.isoformat(),
            "used_at": t.used_at.isoformat() if t.used_at else None,
        }

    def _from_document(self, doc: dict) -> PasswordResetToken:
        used = doc.get("used_at")
        return PasswordResetToken(
            id=UUID(doc["_id"]),
            user_id=UUID(doc["user_id"]),
            token_hash=doc["token_hash"],
            expires_at=_as_dt(doc["expires_at"]),
            created_at=_as_dt(doc["created_at"]),
            used_at=_as_dt(used) if used else None,
        )
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python -m pytest tests/iam/test_mongo_reset_token_repo.py -v`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/iam/infrastructure/persistence/mongo_password_reset_token_repository.py \
        tests/iam/test_mongo_reset_token_repo.py
git commit -m "feat(iam): repositorio Mongo del token de reset (hash unico + indice TTL)"
```

---

### Task 3: Infraestructura — servicio de email Brevo (SMTP + modo dev)

**Files:**
- Create: `src/iam/infrastructure/email/__init__.py` (vacío)
- Create: `src/iam/infrastructure/email/brevo_email_service.py`
- Test: `tests/iam/test_brevo_email_service.py`

**Interfaces:**
- Consumes: `EmailService` (Task 1), `Settings` (`src/shared/config.py`).
- Produces: `BrevoEmailService(settings)` que cumple `EmailService`. Método puro `_build_message(to_email, to_name, reset_link) -> EmailMessage`; `send_password_reset` usa SMTP en `asyncio.to_thread` si hay credenciales, o **modo dev** (loguea el enlace) si faltan.

Nota: este servicio lee la config que agrega la Task 4. Para no acoplar el orden, el constructor recibe cualquier objeto con los atributos `brevo_smtp_host/port/user/key`, `email_sender_name`, `email_sender_address`; el test usa un objeto simple, así que este task no depende de que `config.py` ya tenga los campos.

- [ ] **Step 1: Escribir el test que falla**

`tests/iam/test_brevo_email_service.py`:

```python
import logging
from dataclasses import dataclass

import pytest

from src.iam.infrastructure.email.brevo_email_service import BrevoEmailService


@dataclass
class _Cfg:
    brevo_smtp_host: str = "smtp-relay.brevo.com"
    brevo_smtp_port: int = 587
    brevo_smtp_user: str = ""
    brevo_smtp_key: str = ""
    email_sender_name: str = "SitRight"
    email_sender_address: str = ""


LINK = "https://sitright-web-client.netlify.app/reset-password?token=abc"


def test_build_message_incluye_remitente_destino_y_enlace():
    svc = BrevoEmailService(_Cfg(email_sender_address="no-reply@sitright.app"))
    msg = svc._build_message("u@correo.com", "Ana", LINK)
    assert msg["From"] == "SitRight <no-reply@sitright.app>"
    assert "u@correo.com" in msg["To"]
    assert LINK in msg.get_content()


async def test_modo_dev_loguea_el_enlace_si_no_hay_credenciales(caplog):
    svc = BrevoEmailService(_Cfg())  # sin user/key/sender -> modo dev
    with caplog.at_level(logging.INFO):
        await svc.send_password_reset("u@correo.com", "Ana", LINK)
    assert any(LINK in r.message for r in caplog.records)
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/iam/test_brevo_email_service.py -v`
Expected: FAIL con `ModuleNotFoundError` del servicio.

- [ ] **Step 3: Implementar el servicio**

`src/iam/infrastructure/email/__init__.py`: archivo vacío.

`src/iam/infrastructure/email/brevo_email_service.py`:

```python
import asyncio
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """Envía correos transaccionales por el relay SMTP de Brevo. Si faltan
    credenciales, corre en modo dev: no envía y loguea el enlace (útil en local)."""

    def __init__(self, settings) -> None:
        self._host = settings.brevo_smtp_host
        self._port = settings.brevo_smtp_port
        self._user = settings.brevo_smtp_user
        self._key = settings.brevo_smtp_key
        self._sender_name = settings.email_sender_name
        self._sender_address = settings.email_sender_address

    def _configured(self) -> bool:
        return bool(self._user and self._key and self._sender_address)

    def _build_message(self, to_email: str, to_name: str, reset_link: str) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = "Restablece tu contrasena de SitRight"
        msg["From"] = f"{self._sender_name} <{self._sender_address}>"
        msg["To"] = f"{to_name} <{to_email}>"
        msg.set_content(
            f"Hola {to_name},\n\n"
            "Recibimos una solicitud para restablecer tu contrasena de SitRight.\n"
            "Abre este enlace para crear una nueva (caduca en 1 hora):\n\n"
            f"{reset_link}\n\n"
            "Si no fuiste tu, ignora este correo.\n"
        )
        msg.add_alternative(
            f"<p>Hola {to_name},</p>"
            "<p>Recibimos una solicitud para restablecer tu contrasena de SitRight.</p>"
            f'<p><a href="{reset_link}">Crear una nueva contrasena</a> (caduca en 1 hora).</p>'
            "<p>Si no fuiste tu, ignora este correo.</p>",
            subtype="html",
        )
        return msg

    def _send_sync(self, msg: EmailMessage) -> None:
        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            smtp.starttls()
            smtp.login(self._user, self._key)
            smtp.send_message(msg)

    async def send_password_reset(
        self, to_email: str, to_name: str, reset_link: str
    ) -> None:
        if not self._configured():
            logger.info(
                "[reset] (modo dev, sin SMTP) enlace para %s: %s", to_email, reset_link
            )
            return
        msg = self._build_message(to_email, to_name, reset_link)
        await asyncio.to_thread(self._send_sync, msg)
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `python -m pytest tests/iam/test_brevo_email_service.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add src/iam/infrastructure/email/__init__.py \
        src/iam/infrastructure/email/brevo_email_service.py \
        tests/iam/test_brevo_email_service.py
git commit -m "feat(iam): servicio de email Brevo (SMTP) con modo dev que loguea el enlace"
```

---

### Task 4: Config + casos de uso (`UserCommandService`) + wiring en `main.py`

Este task es atómico: al agregar dependencias **requeridas** al `@dataclass` `UserCommandService`, hay que actualizar `main.py` en el mismo commit para que el arranque (y toda la suite de tests de endpoints) siga verde.

**Files:**
- Modify: `src/shared/config.py`
- Modify: `src/iam/domain/services/user_command_service.py` (interfaz)
- Modify: `src/iam/application/internal/commandservices/user_command_service.py`
- Modify: `src/main.py` (imports + construcción + índices)
- Test: `tests/iam/test_password_reset_service.py`

**Interfaces:**
- Consumes: `PasswordResetToken`, `PasswordResetTokenRepository`, `EmailService`, `ResetPasswordCommand`, `InvalidResetTokenError` (Task 1); `MongoPasswordResetTokenRepository` (Task 2); `BrevoEmailService` (Task 3).
- Produces:
  - `UserCommandService` gana los campos `reset_token_repository: PasswordResetTokenRepository`, `email_service: EmailService`, `app_base_url: str`, `reset_token_ttl_seconds: int`.
  - `handle_request_password_reset` deja de ser stub (genera+guarda token, envía correo).
  - `handle_reset_password(command: ResetPasswordCommand) -> None` (nuevo).

- [ ] **Step 1: Agregar la config**

En `src/shared/config.py`, dentro de `class Settings`, después de `vest_pairing_code`:

```python
    app_base_url: str = "https://sitright-web-client.netlify.app"
    reset_token_expires_seconds: int = 3600
    brevo_smtp_host: str = "smtp-relay.brevo.com"
    brevo_smtp_port: int = 587
    brevo_smtp_user: str = ""
    brevo_smtp_key: str = ""
    email_sender_name: str = "SitRight"
    email_sender_address: str = ""
```

- [ ] **Step 2: Escribir el test que falla**

`tests/iam/test_password_reset_service.py`:

```python
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
```

- [ ] **Step 3: Correr el test y verificar que falla**

Run: `python -m pytest tests/iam/test_password_reset_service.py -v`
Expected: FAIL — `ImportError: cannot import name '_hash_token'` / falta `handle_reset_password` / faltan campos del dataclass.

- [ ] **Step 4: Implementar los casos de uso**

En `src/iam/application/internal/commandservices/user_command_service.py`:

4a. Agregar imports (después de los imports existentes de `datetime`/`uuid4`):

```python
import hashlib
import secrets
from datetime import timedelta

from ....domain.entities.password_reset_token import PasswordResetToken
from ....domain.model.commands.reset_password_command import (
    InvalidResetTokenError,
    ResetPasswordCommand,
)
from ....domain.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from ....domain.services.email_service import EmailService
```

(el módulo ya importa `from datetime import datetime` y `from uuid import uuid4`; mantenerlos).

4b. Helper a nivel de módulo (después de `logger = logging.getLogger(__name__)`):

```python
def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
```

4c. Agregar campos al `@dataclass class UserCommandService` (después de `token_service: TokenService`):

```python
    reset_token_repository: PasswordResetTokenRepository
    email_service: EmailService
    app_base_url: str
    reset_token_ttl_seconds: int
```

4d. Reemplazar el cuerpo de `handle_request_password_reset` por:

```python
    async def handle_request_password_reset(
        self, command: RequestPasswordResetCommand
    ) -> None:
        # HU-27 — respuesta uniforme aunque el correo no exista (AC2).
        normalized = command.email.lower().strip()
        user = await self.user_repository.find_by_email(normalized)
        if user is None:
            logger.info(
                "[forgot-password] solicitud para correo no registrado: %s", normalized
            )
            return
        # Invalida enlaces previos y genera uno nuevo (crudo por correo, hash en BD).
        await self.reset_token_repository.invalidate_for_user(user.id)
        raw = secrets.token_urlsafe(32)
        now = datetime.utcnow()
        token = PasswordResetToken(
            id=uuid4(),
            user_id=user.id,
            token_hash=_hash_token(raw),
            expires_at=now + timedelta(seconds=self.reset_token_ttl_seconds),
            created_at=now,
        )
        await self.reset_token_repository.save(token)
        link = f"{self.app_base_url}/reset-password?token={raw}"
        try:
            await self.email_service.send_password_reset(user.email, user.name, link)
        except Exception:
            logger.warning(
                "[forgot-password] fallo enviando el correo a user_id=%s",
                user.id,
                exc_info=True,
            )
```

4e. Agregar el nuevo handler (justo debajo del anterior):

```python
    async def handle_reset_password(self, command: ResetPasswordCommand) -> None:
        # HU-27 — fija la nueva contrasena si el token es valido (no usado, no vencido).
        if len(command.new_password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        token = await self.reset_token_repository.find_by_hash(
            _hash_token(command.token)
        )
        now = datetime.utcnow()
        if token is None or not token.is_valid(now):
            raise InvalidResetTokenError("El enlace no es válido o expiró")
        user = await self.user_repository.find_by_id(token.user_id)
        if user is None or not user.is_active:
            raise InvalidResetTokenError("El enlace no es válido o expiró")
        user.password_hash = self.password_service.hash(command.new_password)
        user.updated_at = now
        await self.user_repository.save(user)
        # Un solo uso: marca el usado e invalida todos los del usuario.
        await self.reset_token_repository.mark_used(token.id, now)
        await self.reset_token_repository.invalidate_for_user(user.id)
```

4f. En la interfaz `src/iam/domain/services/user_command_service.py`: agregar el import y el método.

Import (junto a los otros `from ..model.commands...`):

```python
from ..model.commands.reset_password_command import ResetPasswordCommand
```

Método (dentro de `class IUserCommandService`, tras `handle_request_password_reset`):

```python
    async def handle_reset_password(self, command: ResetPasswordCommand) -> None: ...
```

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `python -m pytest tests/iam/test_password_reset_service.py -v`
Expected: PASS (9 passed).

- [ ] **Step 6: Actualizar el wiring en `main.py`**

En `src/main.py`:

6a. Imports (junto a los `from .iam.infrastructure...`):

```python
from .iam.infrastructure.email.brevo_email_service import BrevoEmailService
from .iam.infrastructure.persistence.mongo_password_reset_token_repository import (
    MongoPasswordResetTokenRepository,
)
```

6b. En `lifespan`, tras `token_service = JwtTokenService(...)` / `set_token_service(token_service)` y antes de construir `user_command_service`:

```python
    reset_token_repo = MongoPasswordResetTokenRepository(db)
    await reset_token_repo.ensure_indexes()
    email_service = BrevoEmailService(settings)
```

6c. Reemplazar la construcción de `user_command_service` por:

```python
    user_command_service = UserCommandService(
        user_repository=user_repo,
        notification_repository=notif_repo,
        password_service=password_service,
        token_service=token_service,
        reset_token_repository=reset_token_repo,
        email_service=email_service,
        app_base_url=settings.app_base_url,
        reset_token_ttl_seconds=settings.reset_token_expires_seconds,
    )
```

- [ ] **Step 7: Verificar tests iam + que `main.py` importa (wiring válido)**

Run: `./venv/Scripts/python.exe -m pytest tests/iam -q`
Expected: PASS (todos los tests de `tests/iam`).

Run: `./venv/Scripts/python.exe -c "import src.main"`
Expected: sin error (importar `main` construye el objeto `app` pero NO corre el `lifespan`; valida que el wiring nuevo compila e importa).

Nota de entorno: la suite de endpoints (`pytest -q` completo) arranca el `lifespan`,
que se conecta a MongoDB (`seed_demo_users`). En este entorno no hay Mongo, así que
esos tests se cuelgan y **no se corren aquí**; se validan con Mongo disponible en CI/dev.

- [ ] **Step 8: Commit**

```bash
git add src/shared/config.py \
        src/iam/domain/services/user_command_service.py \
        src/iam/application/internal/commandservices/user_command_service.py \
        src/main.py tests/iam/test_password_reset_service.py
git commit -m "feat(iam): caso de uso de recuperacion de contrasena (token + correo) y wiring"
```

---

### Task 5: REST — `POST /auth/reset-password`

**Files:**
- Modify: `src/iam/interfaces/schemas/auth_schema.py`
- Modify: `src/iam/interfaces/rest/auth_router.py`
- Test: `tests/iam/test_reset_password_endpoint.py`

**Interfaces:**
- Consumes: `ResetPasswordCommand`, `InvalidResetTokenError` (Task 1); `handle_reset_password` (Task 4); `get_user_command_service` (existente en `auth_router`).
- Produces: `POST /api/v1/auth/reset-password` → `204` OK; `400` "El enlace no es válido o expiró" (token inválido/expirado/usado o contraseña corta); `422` validación Pydantic. Schema `ResetPasswordRequest { token: str, new_password: str (min_length=8) }`.

- [ ] **Step 1: Escribir el test que falla**

`tests/iam/test_reset_password_endpoint.py`:

```python
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
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `python -m pytest tests/iam/test_reset_password_endpoint.py -v`
Expected: FAIL — el endpoint no existe (404) / `ResetPasswordRequest` no existe.

- [ ] **Step 3: Agregar el schema**

En `src/iam/interfaces/schemas/auth_schema.py`, al final:

```python
class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)
```

- [ ] **Step 4: Agregar el endpoint**

En `src/iam/interfaces/rest/auth_router.py`:

4a. Extender los imports existentes:

```python
from ...domain.model.commands.reset_password_command import (
    InvalidResetTokenError,
    ResetPasswordCommand,
)
```

y agregar `ResetPasswordRequest` al import de `..schemas.auth_schema`.

4b. Agregar el endpoint (después de `forgot_password`):

```python
@router.post(
    "/reset-password",
    status_code=204,
    summary="Restablecer contraseña con el token del correo",
    responses={
        204: {"description": "Contraseña actualizada."},
        400: {"description": "El enlace no es válido o expiró."},
        **PYDANTIC_VALIDATION,
    },
)
async def reset_password(
    request: ResetPasswordRequest,
    service: Annotated[IUserCommandService, Depends(get_user_command_service)],
) -> Response:
    """Fija la nueva contraseña usando el token recibido por correo (HU-27)."""
    try:
        await service.handle_reset_password(
            ResetPasswordCommand(token=request.token, new_password=request.new_password)
        )
    except (InvalidResetTokenError, ValueError):
        raise HTTPException(status_code=400, detail="El enlace no es válido o expiró")
    return Response(status_code=204)
```

(`Response`, `HTTPException`, `Depends`, `Annotated` e `IUserCommandService` ya están importados en el archivo.)

- [ ] **Step 5: Correr el test y verificar que pasa**

Run: `python -m pytest tests/iam/test_reset_password_endpoint.py -v`
Expected: PASS (3 passed).

- [ ] **Step 6: Correr los tests iam**

Run: `./venv/Scripts/python.exe -m pytest tests/iam -q`
Expected: PASS (todos los tests de `tests/iam`, incluido el nuevo del endpoint).

Nota: la suite de endpoints completa (`pytest -q`) requiere MongoDB por el `lifespan`;
no se corre en este entorno (ver nota en Task 4).

- [ ] **Step 7: Commit**

```bash
git add src/iam/interfaces/schemas/auth_schema.py \
        src/iam/interfaces/rest/auth_router.py \
        tests/iam/test_reset_password_endpoint.py
git commit -m "feat(iam): endpoint POST /auth/reset-password"
```

---

## Notas de despliegue (no son tareas de código)

Variables de entorno del backend en Render (sin ellas, corre en modo dev y loguea el enlace):

```
APP_BASE_URL=https://sitright-web-client.netlify.app
BREVO_SMTP_USER=<login SMTP de Brevo>
BREVO_SMTP_KEY=<SMTP key de Brevo>
EMAIL_SENDER_ADDRESS=<remitente verificado en Brevo>
```

`render.yaml` puede declarar estas variables (sin valores secretos, marcadas para
completar en el panel). Fuera del alcance de este plan de código.
