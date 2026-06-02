from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class SendVestCommand:
    """Comando del backend hacia el chaleco (recalibrate / restart / firmware_update)."""

    device_id: UUID
    command_type: str  # "recalibrate" | "restart" | "firmware_update"
    firmware_version: str | None = None
