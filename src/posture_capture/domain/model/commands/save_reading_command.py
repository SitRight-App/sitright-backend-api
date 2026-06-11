from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SaveReadingCommand:
    reading_id: UUID
    vest_id: str
    cervical: tuple[float, float, float]
    dorsal: tuple[float, float, float]
    lumbar: tuple[float, float, float]
    timestamp: datetime
    battery_percent: int = 100
    session_id: UUID | None = None
