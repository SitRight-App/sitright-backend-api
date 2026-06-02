from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DeactivateUserCommand:
    user_id: UUID


class CannotDeactivateAdminError(Exception):
    """HU-30 AC2 — no se permite desactivar otra cuenta admin desde el panel."""
