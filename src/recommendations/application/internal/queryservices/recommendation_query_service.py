"""Implementación de IRecommendationQueryService."""
from dataclasses import dataclass
from datetime import datetime, timezone

from ....domain.entities.applied_recommendation import AppliedRecommendation
from ....domain.model.queries.get_recommendations_query import (
    GetRecommendationsByPostureQuery,
    ListAllRecommendationsQuery,
)
from ....domain.model.queries.list_applied_recommendations_query import (
    ListAppliedRecommendationsQuery,
)
from ....domain.repositories.applied_recommendation_repository import (
    AppliedRecommendationRepository,
)
from ...get_recommendations_handler import _CATALOG, VALID_CLASSES, Recommendation


@dataclass
class RecommendationQueryService:
    applied_repository: AppliedRecommendationRepository

    async def handle_list_by_posture(
        self, query: GetRecommendationsByPostureQuery
    ) -> list[Recommendation]:
        if query.posture_class not in VALID_CLASSES:
            raise ValueError(
                f"Clase postural inválida: '{query.posture_class}'. "
                f"Valores válidos: {VALID_CLASSES}"
            )
        return [r for r in _CATALOG if query.posture_class in r.posture_classes]

    async def handle_list_all(
        self, _query: ListAllRecommendationsQuery
    ) -> list[Recommendation]:
        return list(_CATALOG)

    async def handle_list_applied(
        self, query: ListAppliedRecommendationsQuery
    ) -> list[AppliedRecommendation]:
        target_day = query.day or datetime.now(timezone.utc).date()
        return await self.applied_repository.list_for_day(query.user_id, target_day)
