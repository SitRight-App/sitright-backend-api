"""Port que lee las lecturas de una sesión por `session_id` (para la timeline).

La impl vive en `infrastructure/external/session_readings_reader.py`.
"""
from typing import Protocol
from uuid import UUID

from ..value_objects.session_timeline import SessionTimelinePoint


class SessionReadingsReader(Protocol):
    async def read_timeline(self, session_id: UUID) -> list[SessionTimelinePoint]: ...
