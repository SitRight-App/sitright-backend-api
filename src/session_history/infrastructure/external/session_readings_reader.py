"""Lee las lecturas de una sesión por `session_id` desde `posture_readings`.

Mismo patrón cross-context en solo lectura que MongoReadingsAggregator. Devuelve
la forma ligera (clase, confianza, timestamp) que alimenta la línea de tiempo y
las estadísticas derivadas del reporte de sesión.
"""
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...domain.value_objects.session_timeline import SessionTimelinePoint

# Tope defensivo (≈9 h a 5 s ≈ 6500).
_MAX_READINGS = 7000


class MongoSessionReadingsReader:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["posture_readings"]

    async def read_timeline(self, session_id: UUID) -> list[SessionTimelinePoint]:
        cursor = (
            self._col.find(
                {"session_id": str(session_id)},
                projection={"posture_class": 1, "confidence": 1, "timestamp": 1},
            )
            .sort("timestamp", 1)
            .limit(_MAX_READINGS)
        )
        return [
            SessionTimelinePoint(
                reading_id=str(doc["_id"]),
                posture_class=doc.get("posture_class", "indeterminate"),
                confidence=float(doc.get("confidence", 0.0)),
                timestamp=doc.get("timestamp", ""),
            )
            async for doc in cursor
        ]
