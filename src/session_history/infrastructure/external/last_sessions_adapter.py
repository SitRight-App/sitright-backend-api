from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoLastSessionsAdapter:
    """Devuelve el timestamp de la última sesión de cada usuario.

    Usado por el panel admin (HU-29 AC1) para mostrar "última sesión" por
    usuario sin necesitar un GET por cada uno.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["posture_sessions"]

    async def get_last_session_by_user(
        self, user_ids: list[UUID]
    ) -> dict[UUID, str | None]:
        if not user_ids:
            return {}
        ids_str = [str(uid) for uid in user_ids]
        pipeline = [
            {"$match": {"user_id": {"$in": ids_str}}},
            {"$sort": {"started_at": -1}},
            {
                "$group": {
                    "_id": "$user_id",
                    "last_started_at": {"$first": "$started_at"},
                }
            },
        ]
        cursor = self._col.aggregate(pipeline)
        result: dict[UUID, str | None] = {uid: None for uid in user_ids}
        async for doc in cursor:
            uid = UUID(doc["_id"])
            result[uid] = doc.get("last_started_at")
        return result
