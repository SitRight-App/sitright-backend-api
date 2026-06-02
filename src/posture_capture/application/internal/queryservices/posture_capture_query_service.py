"""Implementación del PostureCaptureQueryService."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ....domain.entities.posture_reading import PostureReading
from ....domain.model.queries.get_latest_reading_query import GetLatestReadingQuery
from ....domain.model.queries.get_recent_readings_query import GetRecentReadingsQuery
from ....domain.repositories.posture_reading_repository import PostureReadingRepository


@dataclass
class PostureCaptureQueryService:
    posture_reading_repository: PostureReadingRepository

    async def handle_get_latest_reading(
        self, query: GetLatestReadingQuery
    ) -> PostureReading | None:
        return await self.posture_reading_repository.find_latest(vest_id=query.vest_id)

    async def handle_get_recent_readings(
        self, query: GetRecentReadingsQuery
    ) -> list[PostureReading]:
        if query.since is not None or query.until is not None:
            return await self.posture_reading_repository.find_recent(
                vest_id=query.vest_id,
                limit=query.limit,
                since=query.since,
                until=query.until,
            )
        since: datetime | None = None
        if query.minutes is not None:
            since = datetime.now(timezone.utc) - timedelta(minutes=query.minutes)
        return await self.posture_reading_repository.find_recent(
            vest_id=query.vest_id, limit=query.limit, since=since
        )
