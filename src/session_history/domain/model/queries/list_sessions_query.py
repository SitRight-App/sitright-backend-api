from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ListSessionsQuery:
    user_id: UUID
    limit: int = 20
    offset: int = 0
    since: datetime | None = None
    until: datetime | None = None
