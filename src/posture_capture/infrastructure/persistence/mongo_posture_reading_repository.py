from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

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
        })

    async def find_latest(self) -> PostureReading | None:
        doc = await self._col.find_one(sort=[("timestamp", -1)])
        if doc is None:
            return None
        return PostureReading(
            id=UUID(doc["_id"]),
            vest_id=doc["vest_id"],
            cervical=SensorData(doc["cervical"]["ax"], doc["cervical"]["ay"], doc["cervical"]["az"]),
            dorsal=SensorData(doc["dorsal"]["ax"], doc["dorsal"]["ay"], doc["dorsal"]["az"]),
            lumbar=SensorData(doc["lumbar"]["ax"], doc["lumbar"]["ay"], doc["lumbar"]["az"]),
            timestamp=datetime.fromisoformat(doc["timestamp"]),
            posture_class=doc["posture_class"],
            confidence=doc["confidence"],
        )
