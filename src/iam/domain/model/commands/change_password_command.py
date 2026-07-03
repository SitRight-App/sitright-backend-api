from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class ChangePasswordCommand:
    user_id: UUID
    current_password: str
    new_password: str


class InvalidCurrentPasswordError(Exception):
    """La contraseña actual proporcionada no coincide."""
