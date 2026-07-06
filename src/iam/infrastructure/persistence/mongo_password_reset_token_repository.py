from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....shared.datetime_utils import ensure_utc
from ...domain.entities.password_reset_token import PasswordResetToken


def _as_dt(value) -> datetime:
    # Mongo devuelve las BSON Date como naive; las marcas ISO pueden venir sin
    # zona. Se normaliza todo a UTC con zona para no mezclar aware y naive.
    return ensure_utc(value if isinstance(value, datetime) else datetime.fromisoformat(value))


class MongoPasswordResetTokenRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["password_reset_tokens"]

    async def ensure_indexes(self) -> None:
        await self._col.create_index("token_hash", unique=True)
        # Mongo purga automáticamente los documentos vencidos.
        await self._col.create_index("expires_at", expireAfterSeconds=0)

    async def save(self, token: PasswordResetToken) -> None:
        await self._col.replace_one(
            {"_id": str(token.id)}, self._to_document(token), upsert=True
        )

    async def find_by_hash(self, token_hash: str) -> PasswordResetToken | None:
        doc = await self._col.find_one({"token_hash": token_hash})
        return self._from_document(doc) if doc else None

    async def invalidate_for_user(self, user_id: UUID) -> None:
        await self._col.delete_many({"user_id": str(user_id)})

    async def mark_used(self, token_id: UUID, used_at: datetime) -> None:
        await self._col.update_one(
            {"_id": str(token_id)}, {"$set": {"used_at": used_at.isoformat()}}
        )

    def _to_document(self, t: PasswordResetToken) -> dict:
        return {
            "_id": str(t.id),
            "user_id": str(t.user_id),
            "token_hash": t.token_hash,
            "expires_at": t.expires_at,  # BSON Date (para el índice TTL)
            "created_at": t.created_at.isoformat(),
            "used_at": t.used_at.isoformat() if t.used_at else None,
        }

    def _from_document(self, doc: dict) -> PasswordResetToken:
        used = doc.get("used_at")
        return PasswordResetToken(
            id=UUID(doc["_id"]),
            user_id=UUID(doc["user_id"]),
            token_hash=doc["token_hash"],
            expires_at=_as_dt(doc["expires_at"]),
            created_at=_as_dt(doc["created_at"]),
            used_at=_as_dt(used) if used else None,
        )
