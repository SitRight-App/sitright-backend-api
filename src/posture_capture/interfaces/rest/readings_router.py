from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from ...application.commands.save_reading_handler import SaveReadingCommand, SaveReadingHandler
from ...application.queries.get_latest_reading_handler import GetLatestReadingHandler
from ..schemas.reading_schema import LatestReadingResponse, ReadingRequest, ReadingResponse

router = APIRouter(prefix="/api/v1/readings", tags=["posture_capture"])

_handler: SaveReadingHandler | None = None
_latest_handler: GetLatestReadingHandler | None = None


def set_handler(handler: SaveReadingHandler) -> None:
    global _handler
    _handler = handler


def set_latest_handler(handler: GetLatestReadingHandler) -> None:
    global _latest_handler
    _latest_handler = handler


def get_handler() -> SaveReadingHandler:
    if _handler is None:
        raise RuntimeError("SaveReadingHandler not initialized")
    return _handler


def get_latest_handler() -> GetLatestReadingHandler:
    if _latest_handler is None:
        raise RuntimeError("GetLatestReadingHandler not initialized")
    return _latest_handler


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
    handler: Annotated[GetLatestReadingHandler, Depends(get_latest_handler)],
) -> LatestReadingResponse:
    reading = await handler.execute()
    if reading is None:
        raise HTTPException(status_code=404, detail="No hay lecturas registradas aún")
    return LatestReadingResponse(
        id=str(reading.id),
        vest_id=reading.vest_id,
        posture_class=reading.posture_class,
        confidence=reading.confidence,
        timestamp=reading.timestamp.isoformat(),
    )
