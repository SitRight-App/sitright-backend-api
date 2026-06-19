from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user
from ...domain.entities.posture_session import PostureSession
from ...domain.model.commands.close_session_command import CloseSessionCommand
from ...domain.model.commands.delete_session_command import DeleteSessionCommand
from ...domain.model.commands.start_session_command import StartSessionCommand
from ...domain.model.queries.get_session_query import (
    GetActiveSessionQuery,
    GetSessionQuery,
)
from ...domain.model.queries.list_sessions_query import ListSessionsQuery
from ...domain.services.session_command_service import ISessionCommandService
from ...domain.services.session_query_service import ISessionQueryService
from ..schemas.session_schema import (
    CloseSessionRequest,
    SessionResponse,
    SessionSummaryResponse,
    SessionTimelineReadingResponse,
    StartSessionRequest,
    ZoneAnalysisResponse,
    ZoneDeviationResponse,
)
from ....shared.openapi_responses import (
    NOT_FOUND_SESSION,
    PYDANTIC_VALIDATION,
    UNAUTHORIZED,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["session_history"])

_command_service: ISessionCommandService | None = None
_query_service: ISessionQueryService | None = None


def set_command_service(service: ISessionCommandService) -> None:
    global _command_service
    _command_service = service


def set_query_service(service: ISessionQueryService) -> None:
    global _query_service
    _query_service = service


def get_command_service() -> ISessionCommandService:
    if _command_service is None:
        raise RuntimeError("SessionCommandService no inicializado")
    return _command_service


def get_query_service() -> ISessionQueryService:
    if _query_service is None:
        raise RuntimeError("SessionQueryService no inicializado")
    return _query_service


def _to_response(s: PostureSession) -> SessionResponse:
    summary = None
    if s.summary:
        summary = SessionSummaryResponse(
            total_readings=s.summary.total_readings,
            valid_readings=s.summary.valid_readings,
            adequate_percentage=s.summary.adequate_percentage,
            dominant_deviation=s.summary.dominant_deviation,
            total_minutes=s.summary.total_minutes,
            counts_by_class=s.summary.counts_by_class,
        )
    return SessionResponse(
        id=str(s.id),
        user_id=str(s.user_id),
        vest_device_id=str(s.vest_device_id),
        started_at=s.started_at,
        ended_at=s.ended_at,
        status=s.status.value,
        reading_count=s.reading_count,
        note=s.note,
        duration_minutes=s.duration_minutes(),
        summary=summary,
    )


@router.post(
    "",
    status_code=201,
    response_model=SessionResponse,
    summary="Iniciar una sesión de uso del chaleco",
    responses={
        201: {
            "description": (
                "Sesión nueva creada. Si el usuario ya tenía una sesión activa, "
                "devuelve esa misma (idempotente)."
            )
        },
        **UNAUTHORIZED,
        **PYDANTIC_VALIDATION,
    },
)
async def start_session(
    request: StartSessionRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionCommandService, Depends(get_command_service)],
) -> SessionResponse:
    try:
        session = await service.handle_start_session(
            StartSessionCommand(
                user_id=current.user_id,
                vest_device_id=UUID(request.vest_device_id),
                note=request.note,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(session)


@router.post(
    "/{session_id}/close",
    response_model=SessionResponse,
    summary="Cerrar una sesión y calcular su resumen",
    responses={
        200: {
            "description": (
                "Sesión cerrada. El campo `summary` se calcula agregando todas "
                "las lecturas asociadas (porcentaje adecuada, desviación dominante, "
                "duración total, distribución por clase)."
            )
        },
        **UNAUTHORIZED,
        **NOT_FOUND_SESSION,
        **PYDANTIC_VALIDATION,
    },
)
async def close_session(
    session_id: UUID,
    request: CloseSessionRequest,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionCommandService, Depends(get_command_service)],
) -> SessionResponse:
    try:
        session = await service.handle_close_session(
            CloseSessionCommand(session_id=session_id, note=request.note)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(session)


@router.delete(
    "/{session_id}",
    status_code=204,
    summary="Borrar una sesión del historial",
    responses={
        204: {"description": "Sesión borrada."},
        **UNAUTHORIZED,
        **NOT_FOUND_SESSION,
    },
)
async def delete_session(
    session_id: UUID,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionCommandService, Depends(get_command_service)],
) -> None:
    try:
        await service.handle_delete_session(
            DeleteSessionCommand(session_id=session_id, user_id=current.user_id)
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get(
    "/active",
    response_model=SessionResponse,
    summary="Obtener mi sesión activa actual",
    responses={
        200: {"description": "Sesión en estado `active` para el usuario."},
        404: {
            "description": "No hay sesión activa para este usuario.",
            "content": {"application/json": {"example": {"detail": "No tienes una sesión activa"}}},
        },
        **UNAUTHORIZED,
    },
)
async def get_active(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionQueryService, Depends(get_query_service)],
) -> SessionResponse:
    session = await service.handle_get_active_session(
        GetActiveSessionQuery(user_id=current.user_id)
    )
    if session is None:
        raise HTTPException(status_code=404, detail="No tienes una sesión activa")
    return _to_response(session)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Obtener una sesión por id",
    responses={200: {"description": "Detalle completo de la sesión."}, **UNAUTHORIZED, **NOT_FOUND_SESSION},
)
async def get_session(
    session_id: UUID,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionQueryService, Depends(get_query_service)],
) -> SessionResponse:
    session = await service.handle_get_session(GetSessionQuery(session_id=session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return _to_response(session)


@router.get(
    "/{session_id}/zone-analysis",
    response_model=ZoneAnalysisResponse,
    summary="Desviación postural por zona de una sesión",
    responses={
        200: {
            "description": (
                "Desviación de cada zona (cervical, dorsal, lumbar) calculada "
                "geométricamente desde el sensor crudo vs. el neutro de "
                "calibración. Independiente de la clase del modelo ML. Ver ADR-006."
            )
        },
        **UNAUTHORIZED,
        **NOT_FOUND_SESSION,
    },
)
async def get_zone_analysis(
    session_id: UUID,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionQueryService, Depends(get_query_service)],
) -> ZoneAnalysisResponse:
    analysis = await service.handle_zone_analysis(session_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return _zone_analysis_response(analysis)


@router.get(
    "/{session_id}/readings",
    response_model=list[SessionTimelineReadingResponse],
    summary="Lecturas de una sesión (para la línea de tiempo)",
    responses={
        200: {
            "description": (
                "Lecturas de la sesión identificadas por `session_id` (clave "
                "estable), en orden cronológico. Alimentan la línea de tiempo y "
                "las estadísticas del reporte."
            )
        },
        **UNAUTHORIZED,
    },
)
async def get_session_readings(
    session_id: UUID,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionQueryService, Depends(get_query_service)],
) -> list[SessionTimelineReadingResponse]:
    points = await service.handle_session_readings(session_id)
    return [
        SessionTimelineReadingResponse(
            id=p.reading_id,
            posture_class=p.posture_class,
            confidence=p.confidence,
            timestamp=p.timestamp,
        )
        for p in points
    ]


def _zone_analysis_response(analysis) -> ZoneAnalysisResponse:
    return ZoneAnalysisResponse(
        calibrated=analysis.calibrated,
        threshold_degrees=analysis.threshold_degrees,
        total_readings=analysis.total_readings,
        zones={
            zone: ZoneDeviationResponse(
                deviated_pct=d.deviated_pct,
                minutes_in_deviation=d.minutes_in_deviation,
                avg_angle_deg=d.avg_angle_deg,
                peak_angle_deg=d.peak_angle_deg,
                longest_streak_min=d.longest_streak_min,
                episodes=d.episodes,
            )
            for zone, d in analysis.zones.items()
        },
    )


@router.get(
    "",
    response_model=list[SessionResponse],
    summary="Listar mis sesiones",
    responses={
        200: {
            "description": (
                "Sesiones del usuario ordenadas descendentemente por "
                "`started_at`. Soporta filtros `since`/`until` para construir "
                "la vista semanal."
            )
        },
        **UNAUTHORIZED,
    },
)
async def list_sessions(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    service: Annotated[ISessionQueryService, Depends(get_query_service)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[SessionResponse]:
    sessions = await service.handle_list_sessions(
        ListSessionsQuery(
            user_id=current.user_id,
            limit=limit,
            offset=offset,
            since=since,
            until=until,
        )
    )
    return [_to_response(s) for s in sessions]
