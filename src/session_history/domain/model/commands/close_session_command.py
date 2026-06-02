from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CloseSessionCommand:
    session_id: UUID
    note: str | None = None
