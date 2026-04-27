from typing import Protocol

from ..entities.posture_reading import PostureReading


class PostureReadingRepository(Protocol):
    async def save(self, reading: PostureReading) -> None: ...
