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
