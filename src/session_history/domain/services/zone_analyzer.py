"""Port del analizador de desviación por zona (ADR-006).

La impl vive en `infrastructure/external/zone_analyzer.py` (lee las lecturas
crudas de posture_capture y la calibración del chaleco).
"""
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ..value_objects.zone_analysis import SessionZoneAnalysis


class ZoneAnalyzer(Protocol):
    async def analyze(
        self, vest_device_id: UUID, started_at: datetime, ended_at: datetime | None
    ) -> SessionZoneAnalysis: ...
