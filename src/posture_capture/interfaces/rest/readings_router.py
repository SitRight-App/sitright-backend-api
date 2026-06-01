from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user
from ....vest_management.application.queries.get_my_vest_handler import (
    GetMyVestHandler,
    GetMyVestQuery,
)
from ...application.commands.save_reading_handler import SaveReadingCommand, SaveReadingHandler
from ...application.queries.get_latest_reading_handler import GetLatestReadingHandler
from ...application.queries.get_recent_readings_handler import (
    GetRecentReadingsHandler,
    GetRecentReadingsQuery,
)
from ..schemas.reading_schema import (
    LatestReadingResponse,
    ReadingRequest,
    ReadingResponse,
    TimelineReadingResponse,
)

router = APIRouter(prefix="/api/v1/readings", tags=["posture_capture"])

_handler: SaveReadingHandler | None = None
_latest_handler: GetLatestReadingHandler | None = None
_recent_handler: GetRecentReadingsHandler | None = None
_get_my_vest_handler: GetMyVestHandler | None = None


def set_handler(handler: SaveReadingHandler) -> None:
    global _handler
    _handler = handler


def set_latest_handler(handler: GetLatestReadingHandler) -> None:
    global _latest_handler
    _latest_handler = handler


def set_recent_handler(handler: GetRecentReadingsHandler) -> None:
    global _recent_handler
    _recent_handler = handler


def set_get_my_vest_handler(handler: GetMyVestHandler) -> None:
    global _get_my_vest_handler
    _get_my_vest_handler = handler


def get_handler() -> SaveReadingHandler:
    if _handler is None:
        raise RuntimeError("SaveReadingHandler not initialized")
    return _handler


def get_latest_handler() -> GetLatestReadingHandler:
    if _latest_handler is None:
        raise RuntimeError("GetLatestReadingHandler not initialized")
    return _latest_handler


def get_recent_handler() -> GetRecentReadingsHandler:
    if _recent_handler is None:
        raise RuntimeError("GetRecentReadingsHandler not initialized")
    return _recent_handler


def get_my_vest_handler() -> GetMyVestHandler:
    if _get_my_vest_handler is None:
        raise RuntimeError("GetMyVestHandler (readings_router) no inicializado")
    return _get_my_vest_handler


async def _resolve_user_vest_id(
    current: TokenPayload,
    vest_handler: GetMyVestHandler,
) -> str:
    """Devuelve el vest_id (str UUID) del chaleco del usuario o 404 si no tiene."""
    vest = await vest_handler.execute(GetMyVestQuery(user_id=current.user_id))
    if vest is None or not vest.is_linked():
        raise HTTPException(status_code=404, detail="No tienes un chaleco vinculado")
    return str(vest.id)


@router.post("", status_code=201, response_model=ReadingResponse)
async def create_reading(
    request: ReadingRequest,
    handler: Annotated[SaveReadingHandler, Depends(get_handler)],
) -> ReadingResponse:
    command = SaveReadingCommand(
        reading_id=uuid4(),
        vest_id=request.vest_id,
        cervical=tuple(request.cervical),
        dorsal=tuple(request.dorsal),
        lumbar=tuple(request.lumbar),
        timestamp=request.timestamp or datetime.now(timezone.utc),
        battery_percent=request.battery_percent,
    )
    try:
        reading = await handler.execute(command)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return ReadingResponse(
        id=str(reading.id),
        posture_class=reading.posture_class,
        confidence=reading.confidence,
    )


@router.get("/latest", response_model=LatestReadingResponse)
async def get_latest_reading(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[GetLatestReadingHandler, Depends(get_latest_handler)],
    vest_handler: Annotated[GetMyVestHandler, Depends(get_my_vest_handler)],
) -> LatestReadingResponse:
    """Última lectura del chaleco vinculado al usuario autenticado.

    Si el usuario no tiene chaleco vinculado, devuelve 404 — no exponemos
    lecturas de otros chalecos.
    """
    vest_id = await _resolve_user_vest_id(current, vest_handler)
    reading = await handler.execute(vest_id=vest_id)
    if reading is None:
        raise HTTPException(status_code=404, detail="No hay lecturas registradas aún")
    return LatestReadingResponse(
        id=str(reading.id),
        vest_id=reading.vest_id,
        posture_class=reading.posture_class,
        confidence=reading.confidence,
        timestamp=reading.timestamp.isoformat(),
        battery_percent=reading.battery_percent,
    )


@router.get("/recent", response_model=list[TimelineReadingResponse])
async def get_recent_readings(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    handler: Annotated[GetRecentReadingsHandler, Depends(get_recent_handler)],
    vest_handler: Annotated[GetMyVestHandler, Depends(get_my_vest_handler)],
    limit: int = Query(60, ge=1, le=2000),
    minutes: int | None = Query(None, ge=1, le=1440),
    since: datetime | None = Query(None, description="ISO 8601 timestamp inclusivo"),
    until: datetime | None = Query(None, description="ISO 8601 timestamp inclusivo"),
) -> list[TimelineReadingResponse]:
    """Devuelve las lecturas más recientes del chaleco vinculado, ordenadas ascendente por timestamp.

    Modos de uso:
    - Sin filtros: últimas `limit` lecturas.
    - Con `minutes`: últimas N minutos.
    - Con `since` y/o `until`: rango temporal arbitrario (útil para detalle de sesión).
    """
    vest_id = await _resolve_user_vest_id(current, vest_handler)
    readings = await handler.execute(
        GetRecentReadingsQuery(
            vest_id=vest_id, limit=limit, minutes=minutes, since=since, until=until
        )
    )
    return [
        TimelineReadingResponse(
            id=str(r.id),
            posture_class=r.posture_class,
            confidence=r.confidence,
            timestamp=r.timestamp.isoformat(),
        )
        for r in readings
    ]
