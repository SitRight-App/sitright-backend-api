from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...domain.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationType,
)


class MongoNotificationRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["notifications"]

    async def save(self, notification: Notification) -> None:
        await self._col.replace_one(
            {"_id": str(notification.id)},
            self._to_document(notification),
            upsert=True,
        )

    async def find_by_user_id(
        self, user_id: UUID, limit: int = 20, offset: int = 0
    ) -> list[Notification]:
        cursor = (
            self._col.find({"user_id": str(user_id)})
            .sort("sent_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return [self._from_document(doc) async for doc in cursor]

    async def count_unread(self, user_id: UUID) -> int:
        return await self._col.count_documents(
            {"user_id": str(user_id), "is_read": False}
        )

    async def mark_as_read(self, notification_id: UUID) -> None:
        await self._col.update_one(
            {"_id": str(notification_id)},
            {"$set": {"is_read": True, "read_at": datetime.utcnow().isoformat()}},
        )

    async def mark_all_as_read(self, user_id: UUID) -> int:
        result = await self._col.update_many(
            {"user_id": str(user_id), "is_read": False},
            {"$set": {"is_read": True, "read_at": datetime.utcnow().isoformat()}},
        )
        return result.modified_count

    def _to_document(self, n: Notification) -> dict:
        return {
            "_id": str(n.id),
            "user_id": str(n.user_id),
            "type": n.type.value,
            "message": n.message,
            "channel": n.channel.value,
            "sent_at": n.sent_at.isoformat(),
            "is_read": n.is_read,
            "read_at": n.read_at.isoformat() if n.read_at else None,
        }

    def _from_document(self, doc: dict) -> Notification:
        return Notification(
            id=UUID(doc["_id"]),
            user_id=UUID(doc["user_id"]),
            type=NotificationType(doc["type"]),
            message=doc["message"],
            channel=NotificationChannel(doc["channel"]),
            sent_at=datetime.fromisoformat(doc["sent_at"]),
            is_read=doc.get("is_read", False),
            read_at=datetime.fromisoformat(doc["read_at"]) if doc.get("read_at") else None,
        )
