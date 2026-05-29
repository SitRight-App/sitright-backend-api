from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ...domain.entities.posture_reading import PostureReading
from ...domain.repositories.posture_reading_repository import PostureReadingRepository


@dataclass(frozen=True)
class GetRecentReadingsQuery:
    """Parámetros de la consulta de lecturas recientes para el timeline."""

    limit: int = 60
    minutes: int | None = None  # si se especifica, filtra a las últimas `minutes` minutos


class GetRecentReadingsHandler:
    """Devuelve las lecturas más recientes en orden cronológico ascendente."""

    def __init__(self, repo: PostureReadingRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetRecentReadingsQuery) -> list[PostureReading]:
        since: datetime | None = None
        if query.minutes is not None:
            since = datetime.now(timezone.utc) - timedelta(minutes=query.minutes)
        return await self._repo.find_recent(limit=query.limit, since=since)
