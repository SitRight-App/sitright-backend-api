from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.notification_repository import NotificationRepository


@dataclass(frozen=True)
class MarkAllNotificationsReadCommand:
    user_id: UUID


@dataclass
class MarkAllNotificationsReadHandler:
    repo: NotificationRepository

    async def execute(self, command: MarkAllNotificationsReadCommand) -> int:
        return await self.repo.mark_all_as_read(command.user_id)
