from dataclasses import dataclass


@dataclass(frozen=True)
class GetRecommendationsByPostureQuery:
    """Filtra el catálogo de recomendaciones por la clase postural detectada."""

    posture_class: str


@dataclass(frozen=True)
class ListAllRecommendationsQuery:
    """Devuelve el catálogo completo (vista /recommendations)."""
