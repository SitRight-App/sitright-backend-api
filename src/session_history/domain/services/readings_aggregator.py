"""Port que un agregador de lecturas debe satisfacer al cerrar una sesión.

La impl vive en `infrastructure/external/readings_aggregator.py` (lee la
colección de posture_capture y resume).
"""
from typing import Protocol
from uuid import UUID

from ..value_objects.session_summary import SessionSummary


class ReadingsAggregator(Protocol):
    async def aggregate_for_session(self, session_id: UUID) -> SessionSummary: ...
