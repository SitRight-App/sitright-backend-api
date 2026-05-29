from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from ..domain.entities.applied_recommendation import AppliedRecommendation
from ..domain.repositories.applied_recommendation_repository import (
    AppliedRecommendationRepository,
)
from .get_recommendations_handler import _CATALOG


def _ensure_exists(recommendation_id: str) -> None:
    if not any(r.id == recommendation_id for r in _CATALOG):
        raise ValueError(f"Recomendación '{recommendation_id}' no existe en el catálogo")


@dataclass
class MarkRecommendationAppliedHandler:
    repo: AppliedRecommendationRepository

    async def execute(
        self, user_id: UUID, recommendation_id: str
    ) -> AppliedRecommendation:
        _ensure_exists(recommendation_id)
        applied = AppliedRecommendation(
            user_id=user_id,
            recommendation_id=recommendation_id,
            applied_at=datetime.now(timezone.utc),
        )
        await self.repo.add(applied)
        return applied


@dataclass
class UnmarkRecommendationAppliedHandler:
    repo: AppliedRecommendationRepository

    async def execute(
        self, user_id: UUID, recommendation_id: str, day: date | None = None
    ) -> None:
        _ensure_exists(recommendation_id)
        target_day = day or datetime.now(timezone.utc).date()
        await self.repo.remove(user_id, recommendation_id, target_day)


@dataclass
class ListAppliedRecommendationsHandler:
    repo: AppliedRecommendationRepository

    async def execute(
        self, user_id: UUID, day: date | None = None
    ) -> list[AppliedRecommendation]:
        target_day = day or datetime.now(timezone.utc).date()
        return await self.repo.list_for_day(user_id, target_day)
