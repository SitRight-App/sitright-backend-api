"""Interfaz del servicio de queries para recommendations."""
from typing import Protocol

# Recommendation y AppliedRecommendation siguen viviendo en la capa de
# aplicación (el catálogo estático no es persistido). Los importamos desde
# allí para tipear el contrato sin mover los archivos en este commit.
from ...application.get_recommendations_handler import Recommendation
from ..entities.applied_recommendation import AppliedRecommendation
from ..model.queries.get_recommendations_query import (
    GetRecommendationsByPostureQuery,
    ListAllRecommendationsQuery,
)
from ..model.queries.list_applied_recommendations_query import (
    ListAppliedRecommendationsQuery,
)


class IRecommendationQueryService(Protocol):
    async def handle_list_by_posture(
        self, query: GetRecommendationsByPostureQuery
    ) -> list[Recommendation]: ...

    async def handle_list_all(
        self, query: ListAllRecommendationsQuery
    ) -> list[Recommendation]: ...

    async def handle_list_applied(
        self, query: ListAppliedRecommendationsQuery
    ) -> list[AppliedRecommendation]: ...
