from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase


class MongoLinkedVestsAdapter:
    """Resuelve por lote el chaleco vinculado a cada usuario.

    Usado por el panel admin (HU-29 AC1) para mostrar el estado del chaleco
    junto a cada usuario en la tabla principal.
    """

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["vest_devices"]

    async def get_linked_vest_by_user(
        self, user_ids: list[UUID]
    ) -> dict[UUID, dict | None]:
        if not user_ids:
            return {}
        ids_str = [str(uid) for uid in user_ids]
        result: dict[UUID, dict | None] = {uid: None for uid in user_ids}
        cursor = self._col.find({"user_id": {"$in": ids_str}})
        async for doc in cursor:
            uid_str = doc.get("user_id")
            if not uid_str:
                continue
            try:
                uid = UUID(uid_str)
            except ValueError:
                continue
            result[uid] = {
                "mac_address": doc.get("mac_address"),
                "is_calibrated": bool(doc.get("calibration_reference")),
                "linked_at": doc.get("linked_at"),
                "battery_level": doc.get("battery_level", 100),
            }
        return result
