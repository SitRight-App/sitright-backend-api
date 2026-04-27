from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from ...application.commands.save_reading_handler import SaveReadingCommand, SaveReadingHandler
from ..schemas.reading_schema import ReadingRequest, ReadingResponse

router = APIRouter(prefix="/api/v1/readings", tags=["posture_capture"])

_handler: SaveReadingHandler | None = None


def set_handler(handler: SaveReadingHandler) -> None:
    global _handler
    _handler = handler


def get_handler() -> SaveReadingHandler:
    if _handler is None:
        raise RuntimeError("SaveReadingHandler not initialized")
    return _handler


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
