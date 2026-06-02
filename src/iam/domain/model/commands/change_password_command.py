from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ChangePasswordCommand:
    user_id: UUID
    current_password: str
    new_password: str


class InvalidCurrentPasswordError(Exception):
    """HU-28 AC2 — la contraseña actual proporcionada no coincide."""
