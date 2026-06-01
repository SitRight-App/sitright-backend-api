from collections import Counter
from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...domain.value_objects.session_summary import SessionSummary


class MongoReadingsAggregator:
    """Lee directamente de posture_readings para calcular el resumen al cierre.

    Implementa el Protocol ReadingsAggregator declarado en application.
    Cruza el bounded context (lee otra colección) pero solo en modo lectura
    y solo para calcular el SessionSummary al cierre de la sesión.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["posture_readings"]

    async def aggregate_for_session(self, session_id: UUID) -> SessionSummary:
        cursor = self._col.find({"session_id": str(session_id)})
        counts: Counter[str] = Counter()
        total = 0
        valid = 0
        first_ts: str | None = None
        last_ts: str | None = None
        async for doc in cursor:
            total += 1
            posture = doc.get("posture_class", "indeterminate")
            counts[posture] += 1
            if posture != "indeterminate":
                valid += 1
            ts = doc.get("timestamp")
            if ts:
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts

        adequate = counts.get("adequate", 0)
        adequate_pct = (adequate / total * 100.0) if total else 0.0

        deviation_counts = {k: v for k, v in counts.items() if k not in ("adequate", "indeterminate")}
        dominant: str | None = None
        if deviation_counts:
            dominant = max(deviation_counts, key=deviation_counts.get)

        total_minutes = 0.0
        if first_ts and last_ts:
            try:
                start = datetime.fromisoformat(first_ts)
                end = datetime.fromisoformat(last_ts)
                total_minutes = (end - start).total_seconds() / 60.0
            except ValueError:
                total_minutes = 0.0

        return SessionSummary(
            total_readings=total,
            valid_readings=valid,
            adequate_percentage=round(adequate_pct, 2),
            dominant_deviation=dominant,
            total_minutes=round(total_minutes, 2),
            counts_by_class=dict(counts),
        )
