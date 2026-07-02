from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class NotifyEventCommand:
    user_id: UUID
    event_type: str


class InvalidNotificationEventError(Exception):
    """El tipo de evento recibido no corresponde a ninguna notificacion soportada."""
