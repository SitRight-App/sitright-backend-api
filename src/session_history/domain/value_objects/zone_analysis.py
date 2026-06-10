"""Resultado del análisis de desviación postural por zona (ADR-006).

Cada zona (cervical, dorsal, lumbar) se evalúa de forma independiente a partir
del sensor crudo de esa zona contra su neutro de calibración, sin pasar por la
clase del modelo ML.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class ZoneDeviation:
    """Métricas de desviación de una zona durante una sesión."""

    deviated_pct: float
    """% de lecturas de la sesión por encima del umbral."""
    minutes_in_deviation: float
    """Minutos acumulados en desviación (carga total de la zona)."""
    avg_angle_deg: float
    """Ángulo promedio de desviación desde el neutro, en grados."""
    peak_angle_deg: float
    """Ángulo máximo registrado, en grados."""
    longest_streak_min: float
    """Episodio sostenido más largo, en minutos (carga continua)."""
    episodes: int
    """Cantidad de tramos sostenidos de desviación."""


@dataclass(frozen=True)
class SessionZoneAnalysis:
    calibrated: bool
    """False si el chaleco no tiene referencia de calibración: no se puede medir ángulo."""
    threshold_degrees: float
    total_readings: int
    zones: dict[str, ZoneDeviation]
