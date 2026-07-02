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
