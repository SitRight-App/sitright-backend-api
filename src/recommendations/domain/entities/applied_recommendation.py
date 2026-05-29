from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class AppliedRecommendation:
    """Registro de que un usuario marcó una recomendación como aplicada en un día.

    Identificada de forma única por la tripleta (user_id, recommendation_id, day);
    el `day` se deriva de `applied_at` en UTC para la consulta y el upsert.
    """

    user_id: UUID
    recommendation_id: str
    applied_at: datetime
