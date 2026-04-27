from fastapi import APIRouter, HTTPException

from ...application.get_recommendations_handler import GetRecommendationsHandler
from ..schemas.recommendation_schema import RecommendationResponse

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

_handler = GetRecommendationsHandler()


@router.get("/{posture_class}", response_model=list[RecommendationResponse])
async def get_recommendations(posture_class: str) -> list[RecommendationResponse]:
    try:
        recs = _handler.execute(posture_class)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [RecommendationResponse(title=r.title, description=r.description) for r in recs]
