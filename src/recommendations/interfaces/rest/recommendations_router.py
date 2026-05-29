from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user
from ...application.applied_handlers import (
    ListAppliedRecommendationsHandler,
    MarkRecommendationAppliedHandler,
    UnmarkRecommendationAppliedHandler,
)
from ...application.get_recommendations_handler import (
    GetAllRecommendationsHandler,
    GetRecommendationsHandler,
    Recommendation,
)
from ..schemas.recommendation_schema import (
    AppliedRecommendationResponse,
    RecommendationResponse,
    RecommendationStepResponse,
)

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

_handler = GetRecommendationsHandler()
_list_handler = GetAllRecommendationsHandler()

_mark_handler: MarkRecommendationAppliedHandler | None = None
_unmark_handler: UnmarkRecommendationAppliedHandler | None = None
_list_applied_handler: ListAppliedRecommendationsHandler | None = None


def set_mark_handler(h: MarkRecommendationAppliedHandler) -> None:
    global _mark_handler
    _mark_handler = h


def set_unmark_handler(h: UnmarkRecommendationAppliedHandler) -> None:
    global _unmark_handler
    _unmark_handler = h


def set_list_applied_handler(h: ListAppliedRecommendationsHandler) -> None:
    global _list_applied_handler
    _list_applied_handler = h


def get_mark_handler() -> MarkRecommendationAppliedHandler:
    if _mark_handler is None:
        raise RuntimeError("MarkRecommendationAppliedHandler no inicializado")
    return _mark_handler


def get_unmark_handler() -> UnmarkRecommendationAppliedHandler:
    if _unmark_handler is None:
        raise RuntimeError("UnmarkRecommendationAppliedHandler no inicializado")
    return _unmark_handler


def get_list_applied_handler() -> ListAppliedRecommendationsHandler:
    if _list_applied_handler is None:
        raise RuntimeError("ListAppliedRecommendationsHandler no inicializado")
    return _list_applied_handler


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


# IMPORTANTE: las rutas estáticas /applied y /{rec_id}/apply deben declararse
# antes que la ruta dinámica /{posture_class} para que FastAPI las matchee
# primero.


@router.get("/applied", response_model=list[AppliedRecommendationResponse])
async def list_applied_today(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[
        ListAppliedRecommendationsHandler, Depends(get_list_applied_handler)
    ],
) -> list[AppliedRecommendationResponse]:
    """Lista las recomendaciones marcadas como aplicadas hoy por el usuario."""
    applied = await handler.execute(current.user_id)
    return [
        AppliedRecommendationResponse(
            recommendation_id=a.recommendation_id, applied_at=a.applied_at
        )
        for a in applied
    ]


@router.post(
    "/{rec_id}/apply",
    status_code=201,
    response_model=AppliedRecommendationResponse,
)
async def mark_applied(
    rec_id: str,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[
        MarkRecommendationAppliedHandler, Depends(get_mark_handler)
    ],
) -> AppliedRecommendationResponse:
    """Marca una recomendación como aplicada hoy. Idempotente por (usuario, recomendación, día)."""
    try:
        applied = await handler.execute(current.user_id, rec_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AppliedRecommendationResponse(
        recommendation_id=applied.recommendation_id, applied_at=applied.applied_at
    )


@router.delete("/{rec_id}/apply", status_code=204)
async def unmark_applied(
    rec_id: str,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[
        UnmarkRecommendationAppliedHandler, Depends(get_unmark_handler)
    ],
) -> Response:
    """Desmarca una recomendación previamente aplicada hoy."""
    try:
        await handler.execute(current.user_id, rec_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)


@router.get("", response_model=list[RecommendationResponse])
async def list_recommendations() -> list[RecommendationResponse]:
    """Lista el catálogo completo de recomendaciones (página /recommendations)."""
    return [_to_response(r) for r in _list_handler.execute()]


@router.get("/{posture_class}", response_model=list[RecommendationResponse])
async def get_recommendations(posture_class: str) -> list[RecommendationResponse]:
    """Recomendaciones aplicables a una clase postural específica (dashboard)."""
    try:
        recs = _handler.execute(posture_class)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [_to_response(r) for r in recs]
