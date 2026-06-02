"""Implementación de IRecommendationCommandService."""
from dataclasses import dataclass
from datetime import datetime, timezone

from ....domain.entities.applied_recommendation import AppliedRecommendation
from ....domain.model.commands.mark_recommendation_applied_command import (
    MarkRecommendationAppliedCommand,
)
from ....domain.model.commands.unmark_recommendation_applied_command import (
    UnmarkRecommendationAppliedCommand,
)
from ....domain.repositories.applied_recommendation_repository import (
    AppliedRecommendationRepository,
)
from ...get_recommendations_handler import _CATALOG


def _ensure_exists(recommendation_id: str) -> None:
    if not any(r.id == recommendation_id for r in _CATALOG):
        raise ValueError(
            f"Recomendación '{recommendation_id}' no existe en el catálogo"
        )


@dataclass
class RecommendationCommandService:
    applied_repository: AppliedRecommendationRepository

    async def handle_mark_applied(
        self, command: MarkRecommendationAppliedCommand
    ) -> AppliedRecommendation:
        _ensure_exists(command.recommendation_id)
        applied = AppliedRecommendation(
            user_id=command.user_id,
            recommendation_id=command.recommendation_id,
            applied_at=datetime.now(timezone.utc),
        )
        await self.applied_repository.add(applied)
        return applied

    async def handle_unmark_applied(
        self, command: UnmarkRecommendationAppliedCommand
    ) -> None:
        _ensure_exists(command.recommendation_id)
        target_day = command.day or datetime.now(timezone.utc).date()
        await self.applied_repository.remove(
            command.user_id, command.recommendation_id, target_day
        )
