from datetime import date
from typing import Protocol
from uuid import UUID

from ..entities.applied_recommendation import AppliedRecommendation


class AppliedRecommendationRepository(Protocol):
    """Persistencia de las recomendaciones marcadas como aplicadas por un usuario en un día."""

    async def add(self, applied: AppliedRecommendation) -> None:
        """Marca como aplicada. Idempotente para la misma tripleta (user, rec, día)."""

    async def remove(self, user_id: UUID, recommendation_id: str, day: date) -> None:
        """Desmarca una recomendación específica del día indicado."""

    async def list_for_day(
        self, user_id: UUID, day: date
    ) -> list[AppliedRecommendation]:
        """Devuelve todas las recomendaciones aplicadas por el usuario ese día."""
