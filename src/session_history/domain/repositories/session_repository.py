from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..entities.posture_session import PostureSession


class PostureSessionRepository(Protocol):
    async def save(self, session: PostureSession) -> None: ...
    async def find_by_id(self, session_id: UUID) -> PostureSession | None: ...
    async def find_active_by_user(self, user_id: UUID) -> PostureSession | None: ...
    async def find_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[PostureSession]: ...
    async def count_by_user(self, user_id: UUID) -> int: ...
