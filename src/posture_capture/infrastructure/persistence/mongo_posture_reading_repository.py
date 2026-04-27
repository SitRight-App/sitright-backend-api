from motor.motor_asyncio import AsyncIOMotorDatabase

from ...domain.entities.posture_reading import PostureReading


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
