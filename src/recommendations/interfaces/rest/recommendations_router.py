from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user
from ...application.get_recommendations_handler import Recommendation
from ...domain.model.commands.mark_recommendation_applied_command import (
    MarkRecommendationAppliedCommand,
)
from ...domain.model.commands.unmark_recommendation_applied_command import (
    UnmarkRecommendationAppliedCommand,
)
from ...domain.model.queries.get_recommendations_query import (
    GetRecommendationsByPostureQuery,
    ListAllRecommendationsQuery,
)
from ...domain.model.queries.list_applied_recommendations_query import (
    ListAppliedRecommendationsQuery,
)
from ...domain.services.recommendation_command_service import (
    IRecommendationCommandService,
)
from ...domain.services.recommendation_query_service import (
    IRecommendationQueryService,
)
from ..schemas.recommendation_schema import (
    AppliedRecommendationResponse,
    RecommendationResponse,
    RecommendationStepResponse,
)
from ....shared.openapi_responses import UNAUTHORIZED

router = APIRouter(prefix="/api/v1/recommendations", tags=["recommendations"])

_command_service: IRecommendationCommandService | None = None
_query_service: IRecommendationQueryService | None = None


def set_command_service(service: IRecommendationCommandService) -> None:
    global _command_service
    _command_service = service


def set_query_service(service: IRecommendationQueryService) -> None:
    global _query_service
    _query_service = service


def get_command_service() -> IRecommendationCommandService:
    if _command_service is None:
        raise RuntimeError("RecommendationCommandService no inicializado")
    return _command_service


def get_query_service() -> IRecommendationQueryService:
    if _query_service is None:
        raise RuntimeError("RecommendationQueryService no inicializado")
    return _query_service


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
# antes que la ruta dinámica /{posture_class}.


@router.get(
    "/applied",
    response_model=list[AppliedRecommendationResponse],
    summary="Recomendaciones que ya marqué como aplicadas hoy",
    responses={200: {"description": "Lista de aplicaciones del día UTC actual."}, **UNAUTHORIZED},
)
async def list_applied_today(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IRecommendationQueryService, Depends(get_query_service)],
) -> list[AppliedRecommendationResponse]:
    """Lista las recomendaciones marcadas como aplicadas hoy por el usuario."""
    applied = await service.handle_list_applied(
        ListAppliedRecommendationsQuery(user_id=current.user_id)
    )
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
    summary="Marcar una recomendación como aplicada",
    responses={
        201: {"description": "Recomendación marcada (idempotente por usuario+recomendación+día)."},
        404: {
            "description": "La recomendación no existe en el catálogo.",
            "content": {
                "application/json": {
                    "example": {"detail": "Recomendación 'foo' no existe en el catálogo"}
                }
            },
        },
        **UNAUTHORIZED,
    },
)
async def mark_applied(
    rec_id: str,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IRecommendationCommandService, Depends(get_command_service)],
) -> AppliedRecommendationResponse:
    """Marca una recomendación como aplicada hoy. Idempotente."""
    try:
        applied = await service.handle_mark_applied(
            MarkRecommendationAppliedCommand(
                user_id=current.user_id, recommendation_id=rec_id
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return AppliedRecommendationResponse(
        recommendation_id=applied.recommendation_id, applied_at=applied.applied_at
    )


@router.delete(
    "/{rec_id}/apply",
    status_code=204,
    summary="Desmarcar una recomendación aplicada por error",
    responses={
        204: {"description": "Desmarcada para el día UTC actual."},
        404: {
            "description": "La recomendación no existe en el catálogo.",
            "content": {
                "application/json": {
                    "example": {"detail": "Recomendación 'foo' no existe en el catálogo"}
                }
            },
        },
        **UNAUTHORIZED,
    },
)
async def unmark_applied(
    rec_id: str,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[IRecommendationCommandService, Depends(get_command_service)],
) -> Response:
    """Desmarca una recomendación previamente aplicada hoy."""
    try:
        await service.handle_unmark_applied(
            UnmarkRecommendationAppliedCommand(
                user_id=current.user_id, recommendation_id=rec_id
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return Response(status_code=204)


@router.get(
    "",
    response_model=list[RecommendationResponse],
    summary="Catálogo completo de recomendaciones",
    responses={200: {"description": "Vista `/recommendations` del web client."}, **UNAUTHORIZED},
)
async def list_recommendations(
    service: Annotated[IRecommendationQueryService, Depends(get_query_service)],
) -> list[RecommendationResponse]:
    """Lista el catálogo completo de recomendaciones."""
    recs = await service.handle_list_all(ListAllRecommendationsQuery())
    return [_to_response(r) for r in recs]


@router.get(
    "/{posture_class}",
    response_model=list[RecommendationResponse],
    summary="Recomendaciones filtradas por clase postural",
    responses={
        200: {"description": "Subconjunto del catálogo aplicable a `posture_class`."},
        400: {
            "description": "Clase postural inválida (no está en `{adequate, forward_slouch, excessive_recline, indeterminate}`).",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Clase postural inválida: 'foo'. Valores válidos: {'adequate', 'forward_slouch', 'excessive_recline', 'indeterminate'}"
                    }
                }
            },
        },
        **UNAUTHORIZED,
    },
)
async def get_recommendations(
    posture_class: str,
    service: Annotated[IRecommendationQueryService, Depends(get_query_service)],
) -> list[RecommendationResponse]:
    """Recomendaciones aplicables a una clase postural específica."""
    try:
        recs = await service.handle_list_by_posture(
            GetRecommendationsByPostureQuery(posture_class=posture_class)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [_to_response(r) for r in recs]
