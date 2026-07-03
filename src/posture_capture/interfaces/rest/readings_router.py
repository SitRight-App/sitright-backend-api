import logging
from datetime import datetime, timezone
from typing import Annotated, Protocol
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from ....iam.domain.services.token_service import TokenPayload
from ....iam.interfaces.rest.dependencies import get_current_user
from ....shared.openapi_responses import (
    NOT_FOUND_NO_READINGS,
    NOT_FOUND_VEST,
    PYDANTIC_VALIDATION,
    UNAUTHORIZED,
    VALIDATION_ERROR,
)
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


class ActiveSessionLookupPort(Protocol):
    """Resuelve la sesión activa del usuario para asociar la lectura (ADR-006)."""

    async def active_session_id(self, user_id: UUID) -> UUID | None: ...


_command_service: IPostureCaptureCommandService | None = None
_query_service: IPostureCaptureQueryService | None = None
_vest_query_service: IVestQueryService | None = None
_active_session_lookup: ActiveSessionLookupPort | None = None


def set_active_session_lookup(lookup: ActiveSessionLookupPort) -> None:
    global _active_session_lookup
    _active_session_lookup = lookup


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


@router.post(
    "",
    status_code=201,
    response_model=ReadingResponse,
    summary="Recibir lectura del chaleco",
    responses={
        201: {
            "description": "Lectura almacenada y clasificada por el ML service.",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "posture_class": "forward_slouch",
                        "confidence": 0.94,
                    }
                }
            },
        },
        **VALIDATION_ERROR,
        403: {
            "description": (
                "el chaleco identificado por `vest_id` (MAC) no "
                "está vinculado a ningún usuario registrado."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "detail": "El chaleco no está vinculado a ningún usuario"
                    }
                }
            },
        },
        **PYDANTIC_VALIDATION,
    },
)
async def create_reading(
    request: ReadingRequest,
    command_service: Annotated[
        IPostureCaptureCommandService, Depends(get_command_service)
    ],
    vest_service: Annotated[IVestQueryService, Depends(get_vest_query_service)],
) -> ReadingResponse:
    missing = [
        name
        for name, value in (
            ("vest_id", request.vest_id),
            ("cervical", request.cervical),
            ("dorsal", request.dorsal),
            ("lumbar", request.lumbar),
        )
        if value is None
    ]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Faltan campos obligatorios: {', '.join(missing)}",
        )

    # el identificador del chaleco debe estar vinculado.
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

    # Asocia la lectura a la sesión activa del usuario (si la hay): es la clave
    # estable por la que el reporte agrupa las lecturas de la sesión (ADR-006).
    session_id: UUID | None = None
    if _active_session_lookup is not None and vest.user_id is not None:
        session_id = await _active_session_lookup.active_session_id(vest.user_id)

    command = SaveReadingCommand(
        reading_id=uuid4(),
        # Id interno del chaleco: misma clave con la que guarda el subscriber
        # MQTT y con la que se consultan las lecturas (/latest, /recent).
        vest_id=str(vest.id),
        user_id=vest.user_id,
        cervical=tuple(request.cervical),
        dorsal=tuple(request.dorsal),
        lumbar=tuple(request.lumbar),
        timestamp=request.timestamp or datetime.now(timezone.utc),
        battery_percent=request.battery_percent,
        session_id=session_id,
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


@router.get(
    "/latest",
    response_model=LatestReadingResponse,
    summary="Última lectura del chaleco del usuario",
    responses={
        200: {
            "description": "Lectura más reciente recibida del chaleco vinculado.",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "vest_id": "AA:BB:CC:11:22:33",
                        "posture_class": "adequate",
                        "confidence": 0.92,
                        "timestamp": "2026-06-02T14:30:15+00:00",
                        "battery_percent": 78,
                    }
                }
            },
        },
        **UNAUTHORIZED,
        **NOT_FOUND_VEST,
        **NOT_FOUND_NO_READINGS,
    },
)
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


@router.get(
    "/latest/raw",
    response_model=LatestRawReadingResponse,
    summary="Última lectura con sensores crudos para calibración",
    responses={
        200: {
            "description": (
                "Devuelve los valores ax/ay/az por sensor; el cliente promedia "
                "un muestreo de 5 segundos para construir la referencia."
            ),
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "vest_id": "AA:BB:CC:11:22:33",
                        "cervical": {"ax": 0.1, "ay": 0.2, "az": 9.8},
                        "dorsal": {"ax": 0.05, "ay": 0.1, "az": 9.9},
                        "lumbar": {"ax": 0.0, "ay": 0.15, "az": 9.7},
                        "timestamp": "2026-06-02T14:30:15+00:00",
                    }
                }
            },
        },
        **UNAUTHORIZED,
        **NOT_FOUND_VEST,
        **NOT_FOUND_NO_READINGS,
    },
)
async def get_latest_raw_reading(
    current: Annotated[TokenPayload, Depends(get_current_user)],
    query_service: Annotated[IPostureCaptureQueryService, Depends(get_query_service)],
    vest_service: Annotated[IVestQueryService, Depends(get_vest_query_service)],
) -> LatestRawReadingResponse:
    """Última lectura con sensores crudos — usada por la calibración."""
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


@router.get(
    "/recent",
    response_model=list[TimelineReadingResponse],
    summary="Lecturas recientes del chaleco (timeline)",
    responses={
        200: {
            "description": "Lecturas ordenadas ascendentemente por timestamp.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "posture_class": "adequate",
                            "confidence": 0.94,
                            "timestamp": "2026-06-02T14:25:00+00:00",
                        },
                        {
                            "id": "550e8400-e29b-41d4-a716-446655440001",
                            "posture_class": "forward_slouch",
                            "confidence": 0.81,
                            "timestamp": "2026-06-02T14:25:05+00:00",
                        },
                    ]
                }
            },
        },
        **UNAUTHORIZED,
        **NOT_FOUND_VEST,
    },
)
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
