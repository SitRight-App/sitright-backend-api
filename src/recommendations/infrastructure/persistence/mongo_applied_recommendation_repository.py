from datetime import date
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ...domain.entities.applied_recommendation import AppliedRecommendation


class MongoAppliedRecommendationRepository:
    """Implementación MongoDB de `AppliedRecommendationRepository`.

    Cada documento representa una recomendación aplicada por un usuario en un día.
    La unicidad por (user_id, recommendation_id, day) se garantiza por upsert.
    """

    COLLECTION = "applied_recommendations"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._coll = db[self.COLLECTION]

    async def add(self, applied: AppliedRecommendation) -> None:
        day = applied.applied_at.date().isoformat()
        await self._coll.update_one(
            {
                "user_id": str(applied.user_id),
                "recommendation_id": applied.recommendation_id,
                "day": day,
            },
            {
                "$set": {
                    "user_id": str(applied.user_id),
                    "recommendation_id": applied.recommendation_id,
                    "applied_at": applied.applied_at,
                    "day": day,
                }
            },
            upsert=True,
        )

    async def remove(
        self, user_id: UUID, recommendation_id: str, day: date
    ) -> None:
        await self._coll.delete_one(
            {
                "user_id": str(user_id),
                "recommendation_id": recommendation_id,
                "day": day.isoformat(),
            }
        )

    async def list_for_day(
        self, user_id: UUID, day: date
    ) -> list[AppliedRecommendation]:
        cursor = self._coll.find(
            {"user_id": str(user_id), "day": day.isoformat()}
        ).sort("applied_at", -1)
        results: list[AppliedRecommendation] = []
        async for doc in cursor:
            results.append(
                AppliedRecommendation(
                    user_id=UUID(doc["user_id"]),
                    recommendation_id=doc["recommendation_id"],
                    applied_at=doc["applied_at"],
                )
            )
        return results
