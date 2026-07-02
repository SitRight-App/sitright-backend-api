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
