from datetime import datetime

from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    vest_device_id: str
    note: str | None = None


class CloseSessionRequest(BaseModel):
    note: str | None = None


class SessionSummaryResponse(BaseModel):
    total_readings: int
    valid_readings: int
    adequate_percentage: float
    dominant_deviation: str | None
    total_minutes: float
    counts_by_class: dict[str, int]


class SessionResponse(BaseModel):
    id: str
    user_id: str
    vest_device_id: str
    started_at: datetime
    ended_at: datetime | None
    status: str
    reading_count: int
    note: str | None
    duration_minutes: float | None
    summary: SessionSummaryResponse | None


class ZoneDeviationResponse(BaseModel):
    deviated_pct: float
    minutes_in_deviation: float
    avg_angle_deg: float
    peak_angle_deg: float
    longest_streak_min: float
    episodes: int


class ZoneAnalysisResponse(BaseModel):
    """Desviación por zona derivada del sensor crudo vs. neutro de calibración (ADR-006)."""

    calibrated: bool
    threshold_degrees: float
    total_readings: int
    zones: dict[str, ZoneDeviationResponse]


class SessionTimelineReadingResponse(BaseModel):
    """Forma ligera de una lectura para la línea de tiempo del reporte de sesión."""

    id: str
    posture_class: str
    confidence: float
    timestamp: str
