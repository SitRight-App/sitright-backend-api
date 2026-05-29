from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.notification_repository import NotificationRepository


@dataclass(frozen=True)
class MarkNotificationReadCommand:
    notification_id: UUID


@dataclass
class MarkNotificationReadHandler:
    repo: NotificationRepository

    async def execute(self, command: MarkNotificationReadCommand) -> None:
        await self.repo.mark_as_read(command.notification_id)
