"""Tests de la matemática de desviación por zona (ADR-006).

Verifican el ángulo geométrico desde el neutro de calibración y la agregación
(% desviado, minutos, racha sostenida, episodios). Puros, sin I/O.
"""
from datetime import datetime, timedelta

from src.posture_capture.domain.value_objects.sensor_data import SensorData
from src.session_history.domain.services.zone_analysis_math import (
    aggregate_zone,
    deviation_angle_deg,
)


def test_angle_identico_es_cero():
    n = SensorData(0.0, 0.0, 1.0)
    assert deviation_angle_deg(SensorData(0.0, 0.0, 1.0), n) == 0.0


def test_angle_perpendicular_es_90():
    n = SensorData(0.0, 0.0, 1.0)
    assert round(deviation_angle_deg(SensorData(1.0, 0.0, 0.0), n), 3) == 90.0


def test_angle_45_grados():
    # neutro en +Z; vector a 45° en el plano XZ
    n = SensorData(0.0, 0.0, 1.0)
    v = SensorData(1.0, 0.0, 1.0)
    assert round(deviation_angle_deg(v, n), 1) == 45.0


def test_angle_escala_no_afecta():
    # La magnitud del vector no cambia el ángulo (solo la dirección).
    n = SensorData(0.0, 0.0, 1.0)
    assert round(deviation_angle_deg(SensorData(0.0, 0.0, 0.4), n), 3) == 0.0


def test_vector_cero_no_revienta():
    n = SensorData(0.0, 0.0, 1.0)
    assert deviation_angle_deg(SensorData(0.0, 0.0, 0.0), n) == 0.0


def _times(n: int, step_s: float = 5.0, start: datetime | None = None) -> list[datetime]:
    base = start or datetime(2026, 6, 9, 9, 0, 0)
    return [base + timedelta(seconds=i * step_s) for i in range(n)]


def test_aggregate_vacio():
    z = aggregate_zone([], [], 20.0)
    assert z.deviated_pct == 0.0 and z.episodes == 0


def test_aggregate_pct_y_pico():
    # 10 lecturas, 4 por encima de 20° → 40%
    angles = [5, 30, 35, 10, 8, 40, 22, 12, 6, 7]
    z = aggregate_zone(_times(10), angles, 20.0)
    assert z.deviated_pct == 40.0
    assert z.peak_angle_deg == 40.0


def test_aggregate_racha_y_episodios():
    # Una racha sostenida de 12 lecturas (×5 s = 60 s = 1 min) por encima del umbral,
    # rodeada de lecturas adecuadas. Debe contar 1 episodio y racha ~1 min.
    angles = [5.0] * 3 + [30.0] * 12 + [5.0] * 3
    z = aggregate_zone(_times(18), angles, 20.0)
    assert z.episodes == 1
    # 12 intervalos contiguos de 5 s ≈ 55-60 s según el borde → ~0.9-1.0 min
    assert 0.8 <= z.longest_streak_min <= 1.1


def test_aggregate_tramo_corto_no_es_episodio():
    # Solo 2 lecturas desviadas (10 s) < MIN_EPISODE_S (30 s) → 0 episodios.
    angles = [5.0] * 5 + [30.0, 30.0] + [5.0] * 5
    z = aggregate_zone(_times(12), angles, 20.0)
    assert z.episodes == 0


def test_aggregate_pausa_corta_la_racha():
    # Dos tramos desviados separados por un hueco grande (pausa) → 2 episodios.
    base = datetime(2026, 6, 9, 9, 0, 0)
    times = (
        [base + timedelta(seconds=i * 5) for i in range(8)]  # tramo 1
        + [base + timedelta(minutes=20) + timedelta(seconds=i * 5) for i in range(8)]  # tramo 2 tras pausa
    )
    angles = [30.0] * 16
    z = aggregate_zone(times, angles, 20.0)
    assert z.episodes == 2
