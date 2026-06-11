from datetime import datetime
from typing import Protocol
from uuid import UUID


from ..entities.posture_reading import PostureReading


class PostureReadingRepository(Protocol):
    async def save(self, reading: PostureReading) -> None: ...
    async def find_latest(self, vest_id: str | None = None) -> PostureReading | None: ...
    async def find_recent(
        self,
        *,
        vest_id: str | None = None,
        limit: int = 60,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[PostureReading]: ...
    async def find_by_session(self, session_id: UUID) -> list[PostureReading]: ...
