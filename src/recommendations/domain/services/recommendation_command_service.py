"""Interfaz del servicio de comandos para recommendations."""
from typing import Protocol

from ..entities.applied_recommendation import AppliedRecommendation
from ..model.commands.mark_recommendation_applied_command import (
    MarkRecommendationAppliedCommand,
)
from ..model.commands.unmark_recommendation_applied_command import (
    UnmarkRecommendationAppliedCommand,
)


class IRecommendationCommandService(Protocol):
    async def handle_mark_applied(
        self, command: MarkRecommendationAppliedCommand
    ) -> AppliedRecommendation: ...

    async def handle_unmark_applied(
        self, command: UnmarkRecommendationAppliedCommand
    ) -> None: ...
