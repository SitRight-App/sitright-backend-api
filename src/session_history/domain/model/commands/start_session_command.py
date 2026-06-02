from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class StartSessionCommand:
    user_id: UUID
    vest_device_id: UUID
    note: str | None = None
