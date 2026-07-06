from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....shared.datetime_utils import parse_utc

from ...domain.entities.posture_session import PostureSession
from ...domain.value_objects.session_status import SessionStatus
from ...domain.value_objects.session_summary import SessionSummary


class MongoPostureSessionRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["posture_sessions"]

    async def save(self, session: PostureSession) -> None:
        await self._col.replace_one(
            {"_id": str(session.id)},
            self._to_document(session),
            upsert=True,
        )

    async def delete(self, session_id: UUID) -> None:
        await self._col.delete_one({"_id": str(session_id)})

    async def find_by_id(self, session_id: UUID) -> PostureSession | None:
        doc = await self._col.find_one({"_id": str(session_id)})
        return self._from_document(doc) if doc else None

    async def find_active_by_user(self, user_id: UUID) -> PostureSession | None:
        doc = await self._col.find_one(
            {"user_id": str(user_id), "status": SessionStatus.ACTIVE.value}
        )
        return self._from_document(doc) if doc else None

    async def find_by_user(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[PostureSession]:
        query: dict = {"user_id": str(user_id)}
        if since or until:
            range_filter: dict = {}
            if since:
                range_filter["$gte"] = since.isoformat()
            if until:
                range_filter["$lte"] = until.isoformat()
            query["started_at"] = range_filter

        cursor = (
            self._col.find(query)
            .sort("started_at", -1)
            .skip(offset)
            .limit(limit)
        )
        return [self._from_document(doc) async for doc in cursor]

    async def count_by_user(self, user_id: UUID) -> int:
        return await self._col.count_documents({"user_id": str(user_id)})

    def _to_document(self, s: PostureSession) -> dict:
        return {
            "_id": str(s.id),
            "user_id": str(s.user_id),
            "vest_device_id": str(s.vest_device_id),
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "status": s.status.value,
            "reading_count": s.reading_count,
            "note": s.note,
            "summary": (
                {
                    "total_readings": s.summary.total_readings,
                    "valid_readings": s.summary.valid_readings,
                    "adequate_percentage": s.summary.adequate_percentage,
                    "dominant_deviation": s.summary.dominant_deviation,
                    "total_minutes": s.summary.total_minutes,
                    "counts_by_class": s.summary.counts_by_class,
                }
                if s.summary
                else None
            ),
        }

    def _from_document(self, doc: dict) -> PostureSession:
        summary_doc = doc.get("summary")
        summary = None
        if summary_doc:
            summary = SessionSummary(
                total_readings=summary_doc["total_readings"],
                valid_readings=summary_doc["valid_readings"],
                adequate_percentage=summary_doc["adequate_percentage"],
                dominant_deviation=summary_doc.get("dominant_deviation"),
                total_minutes=summary_doc["total_minutes"],
                counts_by_class=summary_doc.get("counts_by_class", {}),
            )
        return PostureSession(
            id=UUID(doc["_id"]),
            user_id=UUID(doc["user_id"]),
            vest_device_id=UUID(doc["vest_device_id"]),
            started_at=parse_utc(doc["started_at"]),
            ended_at=parse_utc(doc["ended_at"]) if doc.get("ended_at") else None,
            status=SessionStatus(doc["status"]),
            summary=summary,
            reading_count=doc.get("reading_count", 0),
            note=doc.get("note"),
        )
