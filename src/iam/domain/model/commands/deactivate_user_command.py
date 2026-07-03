from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DeactivateUserCommand:
    user_id: UUID


class CannotDeactivateAdminError(Exception):
    """No se permite desactivar otra cuenta admin desde el panel."""
