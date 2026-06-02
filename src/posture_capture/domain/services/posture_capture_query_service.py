"""Interfaz del servicio de queries para posture_capture (timeline + última)."""
from typing import Protocol

from ..entities.posture_reading import PostureReading
from ..model.queries.get_latest_reading_query import GetLatestReadingQuery
from ..model.queries.get_recent_readings_query import GetRecentReadingsQuery


class IPostureCaptureQueryService(Protocol):
    async def handle_get_latest_reading(
        self, query: GetLatestReadingQuery
    ) -> PostureReading | None: ...

    async def handle_get_recent_readings(
        self, query: GetRecentReadingsQuery
    ) -> list[PostureReading]: ...
