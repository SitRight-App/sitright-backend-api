from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CountUnreadNotificationsQuery:
    user_id: UUID
