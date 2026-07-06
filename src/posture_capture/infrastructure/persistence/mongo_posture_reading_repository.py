from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....shared.datetime_utils import parse_utc

from ...domain.entities.posture_reading import PostureReading
from ...domain.value_objects.sensor_data import SensorData


class MongoPostureReadingRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["posture_readings"]

    async def save(self, reading: PostureReading) -> None:
        await self._col.insert_one({
            "_id": str(reading.id),
            "vest_id": reading.vest_id,
            "cervical": {"ax": reading.cervical.ax, "ay": reading.cervical.ay, "az": reading.cervical.az},
            "dorsal": {"ax": reading.dorsal.ax, "ay": reading.dorsal.ay, "az": reading.dorsal.az},
            "lumbar": {"ax": reading.lumbar.ax, "ay": reading.lumbar.ay, "az": reading.lumbar.az},
            "timestamp": reading.timestamp.isoformat(),
            "posture_class": reading.posture_class,
            "confidence": reading.confidence,
            "battery_percent": reading.battery_percent,
            "session_id": str(reading.session_id) if reading.session_id else None,
            "user_id": str(reading.user_id) if reading.user_id else None,
        })

    async def find_latest(self, vest_id: str | None = None) -> PostureReading | None:
        query: dict = {"vest_id": vest_id} if vest_id is not None else {}
        doc = await self._col.find_one(query, sort=[("timestamp", -1)])
        if doc is None:
            return None
        return self._from_doc(doc)

    async def find_recent(
        self,
        *,
        vest_id: str | None = None,
        limit: int = 60,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[PostureReading]:
        query: dict = {}
        if vest_id is not None:
            query["vest_id"] = vest_id
        time_filter: dict[str, str] = {}
        if since is not None:
            time_filter["$gte"] = since.isoformat()
        if until is not None:
            time_filter["$lte"] = until.isoformat()
        if time_filter:
            query["timestamp"] = time_filter
        cursor = (
            self._col.find(query)
            .sort("timestamp", -1)
            .limit(limit)
        )
        docs: list[dict] = []
        async for doc in cursor:
            docs.append(doc)
        # Return ascending so el consumidor recibe la línea temporal en orden cronológico.
        docs.reverse()
        return [self._from_doc(d) for d in docs]

    async def find_by_session(self, session_id: UUID) -> list[PostureReading]:
        cursor = self._col.find({"session_id": str(session_id)}).sort("timestamp", 1)
        return [self._from_doc(doc) async for doc in cursor]

    @staticmethod
    def _from_doc(doc: dict) -> PostureReading:
        sid = doc.get("session_id")
        uid = doc.get("user_id")
        return PostureReading(
            id=UUID(doc["_id"]),
            vest_id=doc["vest_id"],
            cervical=SensorData(doc["cervical"]["ax"], doc["cervical"]["ay"], doc["cervical"]["az"]),
            dorsal=SensorData(doc["dorsal"]["ax"], doc["dorsal"]["ay"], doc["dorsal"]["az"]),
            lumbar=SensorData(doc["lumbar"]["ax"], doc["lumbar"]["ay"], doc["lumbar"]["az"]),
            timestamp=parse_utc(doc["timestamp"]),
            posture_class=doc["posture_class"],
            confidence=doc["confidence"],
            battery_percent=doc.get("battery_percent", 100),
            session_id=UUID(sid) if sid else None,
            user_id=UUID(uid) if uid else None,
        )
