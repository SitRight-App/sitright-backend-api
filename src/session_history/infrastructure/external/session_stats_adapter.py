from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoSessionStatsAdapter:
    """Adaptador que satisface SessionStatsPort (definido en iam.application)
    leyendo directamente la colección de sesiones."""

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["posture_sessions"]

    async def total_sessions(self) -> int:
        return await self._col.count_documents({})

    async def average_adequate_percentage(self) -> float | None:
        # Promedia adequate_percentage de todas las sesiones cerradas con resumen.
        pipeline = [
            {"$match": {"summary.adequate_percentage": {"$exists": True}}},
            {"$group": {"_id": None, "avg": {"$avg": "$summary.adequate_percentage"}}},
        ]
        cursor = self._col.aggregate(pipeline)
        async for doc in cursor:
            value = doc.get("avg")
            if value is None:
                return None
            return round(float(value), 2)
        return None
