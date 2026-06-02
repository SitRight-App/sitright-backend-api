from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetSessionQuery:
    session_id: UUID


@dataclass(frozen=True)
class GetActiveSessionQuery:
    user_id: UUID
