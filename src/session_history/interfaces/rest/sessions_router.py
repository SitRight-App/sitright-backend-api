from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user
from ...application.commands.close_session_handler import (
    CloseSessionCommand,
    CloseSessionHandler,
)
from ...application.commands.start_session_handler import (
    StartSessionCommand,
    StartSessionHandler,
)
from ...application.queries.get_session_handler import (
    GetActiveSessionHandler,
    GetActiveSessionQuery,
    GetSessionHandler,
    GetSessionQuery,
)
from ...application.queries.list_sessions_handler import (
    ListSessionsHandler,
    ListSessionsQuery,
)
from ...domain.entities.posture_session import PostureSession
from ..schemas.session_schema import (
    CloseSessionRequest,
    SessionResponse,
    SessionSummaryResponse,
    StartSessionRequest,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["session_history"])

_start_handler: StartSessionHandler | None = None
_close_handler: CloseSessionHandler | None = None
_get_handler: GetSessionHandler | None = None
_get_active_handler: GetActiveSessionHandler | None = None
_list_handler: ListSessionsHandler | None = None


def set_start_handler(h: StartSessionHandler) -> None:
    global _start_handler
    _start_handler = h


def set_close_handler(h: CloseSessionHandler) -> None:
    global _close_handler
    _close_handler = h


def set_get_handler(h: GetSessionHandler) -> None:
    global _get_handler
    _get_handler = h


def set_get_active_handler(h: GetActiveSessionHandler) -> None:
    global _get_active_handler
    _get_active_handler = h


def set_list_handler(h: ListSessionsHandler) -> None:
    global _list_handler
    _list_handler = h


def get_start_handler() -> StartSessionHandler:
    if _start_handler is None:
        raise RuntimeError("StartSessionHandler no inicializado")
    return _start_handler


def get_close_handler() -> CloseSessionHandler:
    if _close_handler is None:
        raise RuntimeError("CloseSessionHandler no inicializado")
    return _close_handler


def get_get_handler() -> GetSessionHandler:
    if _get_handler is None:
        raise RuntimeError("GetSessionHandler no inicializado")
    return _get_handler


def get_get_active_handler() -> GetActiveSessionHandler:
    if _get_active_handler is None:
        raise RuntimeError("GetActiveSessionHandler no inicializado")
    return _get_active_handler


def get_list_handler() -> ListSessionsHandler:
    if _list_handler is None:
        raise RuntimeError("ListSessionsHandler no inicializado")
    return _list_handler


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


@router.post("", status_code=201, response_model=SessionResponse)
async def start_session(
    request: StartSessionRequest,
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[StartSessionHandler, Depends(get_start_handler)],
) -> SessionResponse:
    try:
        session = await handler.execute(
            StartSessionCommand(
                user_id=current.user_id,
                vest_device_id=UUID(request.vest_device_id),
                note=request.note,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(session)


@router.post("/{session_id}/close", response_model=SessionResponse)
async def close_session(
    session_id: UUID,
    request: CloseSessionRequest,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[CloseSessionHandler, Depends(get_close_handler)],
) -> SessionResponse:
    try:
        session = await handler.execute(
            CloseSessionCommand(session_id=session_id, note=request.note)
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _to_response(session)


@router.get("/active", response_model=SessionResponse)
async def get_active(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[GetActiveSessionHandler, Depends(get_get_active_handler)],
) -> SessionResponse:
    session = await handler.execute(GetActiveSessionQuery(user_id=current.user_id))
    if session is None:
        raise HTTPException(status_code=404, detail="No tienes una sesión activa")
    return _to_response(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: UUID,
    _: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[GetSessionHandler, Depends(get_get_handler)],
) -> SessionResponse:
    session = await handler.execute(GetSessionQuery(session_id=session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    return _to_response(session)


@router.get("", response_model=list[SessionResponse])
async def list_sessions(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[ListSessionsHandler, Depends(get_list_handler)],
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    since: datetime | None = None,
    until: datetime | None = None,
) -> list[SessionResponse]:
    sessions = await handler.execute(
        ListSessionsQuery(
            user_id=current.user_id,
            limit=limit,
            offset=offset,
            since=since,
            until=until,
        )
    )
    return [_to_response(s) for s in sessions]
