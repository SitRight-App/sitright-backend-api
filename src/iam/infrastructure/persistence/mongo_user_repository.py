from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...domain.entities.user import User
from ...domain.value_objects.anthropometric_data import AnthropometricData
from ...domain.value_objects.preferences import Preferences
from ...domain.value_objects.role import Role


class MongoUserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["users"]

    async def save(self, user: User) -> None:
        await self._col.replace_one(
            {"_id": str(user.id)},
            self._to_document(user),
            upsert=True,
        )

    async def find_by_id(self, user_id: UUID) -> User | None:
        doc = await self._col.find_one({"_id": str(user_id)})
        return self._from_document(doc) if doc else None

    async def find_by_email(self, email: str) -> User | None:
        doc = await self._col.find_one({"email": email.lower().strip()})
        return self._from_document(doc) if doc else None

    async def exists_by_email(self, email: str) -> bool:
        count = await self._col.count_documents({"email": email.lower().strip()}, limit=1)
        return count > 0

    async def find_all(self, limit: int = 100, offset: int = 0) -> list[User]:
        cursor = self._col.find({}).sort("created_at", -1).skip(offset).limit(limit)
        return [self._from_document(doc) async for doc in cursor]

    async def count_all(self) -> int:
        return await self._col.count_documents({})

    def _to_document(self, user: User) -> dict:
        return {
            "_id": str(user.id),
            "name": user.name,
            "email": user.email,
            "password_hash": user.password_hash,
            "role": user.role.value,
            "anthropometric_data": {
                "weight_kg": user.anthropometric_data.weight_kg,
                "height_cm": user.anthropometric_data.height_cm,
            },
            "preferences": {
                "email_notifications": user.preferences.email_notifications,
                "alert_threshold_minutes": user.preferences.alert_threshold_minutes,
                "break_reminder_minutes": user.preferences.break_reminder_minutes,
                "language": user.preferences.language,
            },
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat(),
            "updated_at": user.updated_at.isoformat(),
        }

    def _from_document(self, doc: dict) -> User:
        anthro_doc = doc.get("anthropometric_data") or {}
        prefs_doc = doc.get("preferences") or {}
        return User(
            id=UUID(doc["_id"]),
            name=doc["name"],
            email=doc["email"],
            password_hash=doc["password_hash"],
            role=Role(doc["role"]),
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
            anthropometric_data=AnthropometricData(
                weight_kg=anthro_doc.get("weight_kg"),
                height_cm=anthro_doc.get("height_cm"),
            ),
            preferences=Preferences(
                email_notifications=prefs_doc.get("email_notifications", True),
                alert_threshold_minutes=prefs_doc.get("alert_threshold_minutes", 30),
                # HU-12 AC4: default 60 si nunca se configuró.
                break_reminder_minutes=prefs_doc.get("break_reminder_minutes", 60),
                language=prefs_doc.get("language", "es"),
            ),
            is_active=doc.get("is_active", True),
        )
