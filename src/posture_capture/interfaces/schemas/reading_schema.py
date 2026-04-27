from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ReadingRequest(BaseModel):
    vest_id: str
    cervical: list[float] = Field(..., min_length=3, max_length=3)
    dorsal: list[float] = Field(..., min_length=3, max_length=3)
    lumbar: list[float] = Field(..., min_length=3, max_length=3)
    timestamp: Optional[datetime] = None


class ReadingResponse(BaseModel):
    id: str
    posture_class: str
    confidence: float
