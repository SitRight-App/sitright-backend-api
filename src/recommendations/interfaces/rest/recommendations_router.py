from fastapi import APIRouter, HTTPException

from ...application.get_recommendations_handler import (
    GetAllRecommendationsHandler,
    GetRecommendationsHandler,
    Recommendation,
)
from ..schemas.recommendation_schema import (
    RecommendationResponse,
    RecommendationStepResponse,
)

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

_handler = GetRecommendationsHandler()
_list_handler = GetAllRecommendationsHandler()


def _to_response(r: Recommendation) -> RecommendationResponse:
    return RecommendationResponse(
        id=r.id,
        number=r.number,
        title=r.title,
        description=r.description,
        category=r.category,
        icon=r.icon,
        frequency_label=r.frequency_label,
        posture_classes=list(r.posture_classes),
        is_featured=r.is_featured,
        featured_tagline=r.featured_tagline,
        featured_title_emphasis=r.featured_title_emphasis,
        featured_body=r.featured_body,
        steps=[RecommendationStepResponse(body=s.body, meta=s.meta) for s in r.steps],
    )


@router.get("", response_model=list[RecommendationResponse])
async def list_recommendations() -> list[RecommendationResponse]:
    """Lista todas las recomendaciones del catálogo (uso de la página /recommendations)."""
    return [_to_response(r) for r in _list_handler.execute()]


@router.get("/{posture_class}", response_model=list[RecommendationResponse])
async def get_recommendations(posture_class: str) -> list[RecommendationResponse]:
    """Devuelve las recomendaciones aplicables a una clase postural específica."""
    try:
        recs = _handler.execute(posture_class)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [_to_response(r) for r in recs]
