from ...domain.entities.posture_reading import PostureReading
from ...domain.repositories.posture_reading_repository import PostureReadingRepository


class GetLatestReadingHandler:
    def __init__(self, repo: PostureReadingRepository) -> None:
        self._repo = repo

    async def execute(self, vest_id: str | None = None) -> PostureReading | None:
        return await self._repo.find_latest(vest_id=vest_id)
