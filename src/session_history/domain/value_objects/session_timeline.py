"""Punto de la línea de tiempo de una sesión (forma ligera de una lectura)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class SessionTimelinePoint:
    reading_id: str
    posture_class: str
    confidence: float
    timestamp: str
