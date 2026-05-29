from dataclasses import dataclass
from uuid import UUID

from ...domain.entities.notification import Notification
from ...domain.repositories.notification_repository import NotificationRepository


@dataclass
class ListNotificationsQuery:
    user_id: UUID
    limit: int = 20
    offset: int = 0


class ListNotificationsHandler:
    def __init__(self, repo: NotificationRepository) -> None:
        self._repo = repo

    async def execute(self, query: ListNotificationsQuery) -> list[Notification]:
        return await self._repo.find_by_user_id(query.user_id, query.limit, query.offset)
