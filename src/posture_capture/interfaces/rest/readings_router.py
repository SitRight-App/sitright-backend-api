import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user
from ....vest_management.domain.model.queries.get_my_vest_query import GetMyVestQuery
from ....vest_management.domain.model.queries.get_vest_by_mac_query import (
    GetVestByMacQuery,
)
from ....vest_management.domain.services.vest_query_service import IVestQueryService
from ...domain.model.commands.save_reading_command import SaveReadingCommand
from ...domain.model.queries.get_latest_reading_query import GetLatestReadingQuery
from ...domain.model.queries.get_recent_readings_query import GetRecentReadingsQuery
from ...domain.services.posture_capture_command_service import (
    IPostureCaptureCommandService,
)
from ...domain.services.posture_capture_query_service import (
    IPostureCaptureQueryService,
)
from ..schemas.reading_schema import (
    LatestRawReadingResponse,
    LatestReadingResponse,
    ReadingRequest,
    ReadingResponse,
    SensorTriple,
    TimelineReadingResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/readings", tags=["posture_capture"])

_command_service: IPostureCaptureCommandService | None = None
_query_service: IPostureCaptureQueryService | None = None
_vest_query_service: IVestQueryService | None = None


def set_command_service(service: IPostureCaptureCommandService) -> None:
    global _command_service
    _command_service = service


def set_query_service(service: IPostureCaptureQueryService) -> None:
    global _query_service
    _query_service = service


def set_vest_query_service(service: IVestQueryService) -> None:
    global _vest_query_service
    _vest_query_service = service


def get_command_service() -> IPostureCaptureCommandService:
    if _command_service is None:
        raise RuntimeError("PostureCaptureCommandService no inicializado")
    return _command_service


def get_query_service() -> IPostureCaptureQueryService:
    if _query_service is None:
        raise RuntimeError("PostureCaptureQueryService no inicializado")
    return _query_service


def get_vest_query_service() -> IVestQueryService:
    if _vest_query_service is None:
        raise RuntimeError("VestQueryService (readings_router) no inicializado")
    return _vest_query_service


async def _resolve_user_vest_id(
    current: TokenPayload,
    vest_service: IVestQueryService,
) -> str:
    """Devuelve el vest_id (str UUID) del chaleco del usuario o 404 si no tiene."""
    vest = await vest_service.handle_get_my_vest(GetMyVestQuery(user_id=current.user_id))
    if vest is None or not vest.is_linked():
        raise HTTPException(status_code=404, detail="No tienes un chaleco vinculado")
    return str(vest.id)


@router.post("", status_code=201, response_model=ReadingResponse)
async def create_reading(
    request: ReadingRequest,
    command_service: Annotated[
        IPostureCaptureCommandService, Depends(get_command_service)
    ],
    vest_service: Annotated[IVestQueryService, Depends(get_vest_query_service)],
) -> ReadingResponse:
    # HU-02 AC3 — el identificador del chaleco debe estar vinculado.
    vest = await vest_service.handle_get_vest_by_mac(
        GetVestByMacQuery(mac_address=request.vest_id)
    )
    if vest is None or not vest.is_linked():
        logger.warning(
            "[readings] intento de POST de chaleco no vinculado: vest_id=%s",
            request.vest_id,
        )
        raise HTTPException(
            status_code=403,
            detail="El chaleco no está vinculado a ningún usuario",
        )

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
        reading = await command_service.handle_save_reading(command)
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
    query_service: Annotated[IPostureCaptureQueryService, Depends(get_query_service)],
    vest_service: Annotated[IVestQueryService, Depends(get_vest_query_service)],
) -> LatestReadingResponse:
    """Última lectura del chaleco vinculado al usuario autenticado."""
    vest_id = await _resolve_user_vest_id(current, vest_service)
    reading = await query_service.handle_get_latest_reading(
        GetLatestReadingQuery(vest_id=vest_id)
    )
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


@router.get("/latest/raw", response_model=LatestRawReadingResponse)
async def get_latest_raw_reading(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    query_service: Annotated[IPostureCaptureQueryService, Depends(get_query_service)],
    vest_service: Annotated[IVestQueryService, Depends(get_vest_query_service)],
) -> LatestRawReadingResponse:
    """Última lectura con sensores crudos — usada por la calibración (HU-15)."""
    vest_id = await _resolve_user_vest_id(current, vest_service)
    reading = await query_service.handle_get_latest_reading(
        GetLatestReadingQuery(vest_id=vest_id)
    )
    if reading is None:
        raise HTTPException(status_code=404, detail="No hay lecturas registradas aún")
    return LatestRawReadingResponse(
        id=str(reading.id),
        vest_id=reading.vest_id,
        cervical=SensorTriple(
            ax=reading.cervical.ax, ay=reading.cervical.ay, az=reading.cervical.az
        ),
        dorsal=SensorTriple(
            ax=reading.dorsal.ax, ay=reading.dorsal.ay, az=reading.dorsal.az
        ),
        lumbar=SensorTriple(
            ax=reading.lumbar.ax, ay=reading.lumbar.ay, az=reading.lumbar.az
        ),
        timestamp=reading.timestamp.isoformat(),
    )


@router.get("/recent", response_model=list[TimelineReadingResponse])
async def get_recent_readings(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    query_service: Annotated[IPostureCaptureQueryService, Depends(get_query_service)],
    vest_service: Annotated[IVestQueryService, Depends(get_vest_query_service)],
    limit: int = Query(60, ge=1, le=2000),
    minutes: int | None = Query(None, ge=1, le=1440),
    since: datetime | None = Query(None, description="ISO 8601 timestamp inclusivo"),
    until: datetime | None = Query(None, description="ISO 8601 timestamp inclusivo"),
) -> list[TimelineReadingResponse]:
    """Devuelve las lecturas más recientes del chaleco vinculado."""
    vest_id = await _resolve_user_vest_id(current, vest_service)
    readings = await query_service.handle_get_recent_readings(
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
