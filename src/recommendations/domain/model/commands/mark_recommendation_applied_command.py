from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class MarkRecommendationAppliedCommand:
    user_id: UUID
    recommendation_id: str
