from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.notification_repository import NotificationRepository


@dataclass(frozen=True)
class CountUnreadNotificationsQuery:
    user_id: UUID


@dataclass
class CountUnreadNotificationsHandler:
    repo: NotificationRepository

    async def execute(self, query: CountUnreadNotificationsQuery) -> int:
        return await self.repo.count_unread(query.user_id)
