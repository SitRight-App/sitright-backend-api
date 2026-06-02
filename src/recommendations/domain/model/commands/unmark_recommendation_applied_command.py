from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class UnmarkRecommendationAppliedCommand:
    user_id: UUID
    recommendation_id: str
    day: date | None = None
