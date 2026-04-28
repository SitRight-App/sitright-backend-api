from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReadingRequest(BaseModel):
    vest_id: str
    cervical: list[float] = Field(..., min_length=3, max_length=3)
    dorsal: list[float] = Field(..., min_length=3, max_length=3)
    lumbar: list[float] = Field(..., min_length=3, max_length=3)
    timestamp: Optional[datetime] = None
    battery_percent: int = Field(default=100, ge=0, le=100)


class ReadingResponse(BaseModel):
    id: str
    posture_class: str
    confidence: float


class LatestReadingResponse(BaseModel):
    id: str
    vest_id: str
    posture_class: str
    confidence: float
    timestamp: str
    battery_percent: int
