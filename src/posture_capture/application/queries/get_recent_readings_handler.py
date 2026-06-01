from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from ...domain.entities.posture_reading import PostureReading
from ...domain.repositories.posture_reading_repository import PostureReadingRepository


@dataclass(frozen=True)
class GetRecentReadingsQuery:
    """Parámetros de la consulta de lecturas recientes para el timeline.

    - `minutes` y `(since, until)` son mutuamente excluyentes; si se pasan
      `since`/`until` se ignora `minutes`.
    - Si nada se especifica, se devuelven las últimas `limit` lecturas sin filtro temporal.
    - `vest_id` filtra a las lecturas del chaleco del usuario actual.
    """

    limit: int = 60
    minutes: int | None = None
    since: datetime | None = None
    until: datetime | None = None
    vest_id: str | None = None


class GetRecentReadingsHandler:
    """Devuelve las lecturas más recientes en orden cronológico ascendente."""

    def __init__(self, repo: PostureReadingRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetRecentReadingsQuery) -> list[PostureReading]:
        if query.since is not None or query.until is not None:
            return await self._repo.find_recent(
                vest_id=query.vest_id,
                limit=query.limit,
                since=query.since,
                until=query.until,
            )
        since: datetime | None = None
        if query.minutes is not None:
            since = datetime.now(timezone.utc) - timedelta(minutes=query.minutes)
        return await self._repo.find_recent(
            vest_id=query.vest_id, limit=query.limit, since=since
        )
