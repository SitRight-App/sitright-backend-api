from dataclasses import dataclass
from datetime import date
from uuid import UUID


@dataclass(frozen=True)
class ListAppliedRecommendationsQuery:
    user_id: UUID
    day: date | None = None
