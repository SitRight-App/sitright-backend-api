"""Matemática pura del análisis de desviación por zona (ADR-006).

Sin dependencias de I/O para que sea testeable de forma directa. La desviación
de una zona en una lectura es el ángulo entre el vector gravedad medido y el
neutro de calibración de esa zona:

    θ = acos( clamp( (v·n) / (|v|·|n|), -1, 1 ) )   en grados

Es direccionalmente agnóstico (mide magnitud desde el neutro) y robusto al
montaje físico del sensor. Válido solo en condiciones cuasi-estáticas (sedente).
"""
import math
from datetime import datetime

from ....posture_capture.domain.value_objects.sensor_data import SensorData
from ..value_objects.zone_analysis import ZoneDeviation

# Umbral de desviación por zona, en grados desde el neutro de calibración.
# Respaldo (ver ADR-006): ISO 11226 / RULA operacionalizados con IMU en C7/L5
# (Nature Sci Rep 2025), por encima del RMSE ~5° del IMU en sedente. Configurable.
DEFAULT_ZONE_THRESHOLDS_DEG: dict[str, float] = {
    "cervical": 20.0,
    "dorsal": 20.0,
    "lumbar": 20.0,
}

# Intervalo nominal entre lecturas (s). El chaleco publica cada 5 s (ADR-005).
NOMINAL_INTERVAL_S = 5.0
# Hueco máximo (s) que se sigue contando como continuo; por encima se asume pausa.
GAP_CAP_S = 15.0
# Duración mínima (s) para contar un tramo desviado como "episodio".
MIN_EPISODE_S = 30.0


def deviation_angle_deg(v: SensorData, neutral: SensorData) -> float:
    """Ángulo entre el vector medido y el neutro de calibración, en grados."""
    dot = v.ax * neutral.ax + v.ay * neutral.ay + v.az * neutral.az
    nv = math.sqrt(v.ax * v.ax + v.ay * v.ay + v.az * v.az)
    nn = math.sqrt(neutral.ax * neutral.ax + neutral.ay * neutral.ay + neutral.az * neutral.az)
    if nv == 0.0 or nn == 0.0:
        return 0.0
    cos = max(-1.0, min(1.0, dot / (nv * nn)))
    return math.degrees(math.acos(cos))


def aggregate_zone(
    times: list[datetime], angles: list[float], threshold_deg: float
) -> ZoneDeviation:
    """Agrega los ángulos de una zona en métricas de sesión.

    `times` y `angles` deben venir en orden cronológico y tener la misma longitud.
    Los tramos sostenidos se cortan cuando hay un hueco mayor a `GAP_CAP_S`
    (pausa) o cuando una lectura vuelve por debajo del umbral.
    """
    n = len(angles)
    if n == 0:
        return ZoneDeviation(0.0, 0.0, 0.0, 0.0, 0.0, 0)

    deviated = [a > threshold_deg for a in angles]
    deviated_count = sum(deviated)
    pct = deviated_count / n * 100.0
    avg = sum(angles) / n
    peak = max(angles)

    seconds_in_dev = 0.0
    longest_run_s = 0.0
    episodes = 0
    run_s = 0.0
    run_active = False

    def close_run() -> None:
        nonlocal longest_run_s, episodes, run_s, run_active
        if run_active:
            longest_run_s = max(longest_run_s, run_s)
            if run_s >= MIN_EPISODE_S:
                episodes += 1
        run_s = 0.0
        run_active = False

    for i in range(n):
        if i < n - 1:
            dt = (times[i + 1] - times[i]).total_seconds()
            contiguous = 0.0 < dt <= GAP_CAP_S
            slice_s = dt if contiguous else NOMINAL_INTERVAL_S
        else:
            contiguous = False
            slice_s = NOMINAL_INTERVAL_S

        if deviated[i]:
            seconds_in_dev += slice_s
            run_s += slice_s
            run_active = True
            if not contiguous:
                close_run()
        else:
            close_run()

    close_run()

    return ZoneDeviation(
        deviated_pct=round(pct, 1),
        minutes_in_deviation=round(seconds_in_dev / 60.0, 1),
        avg_angle_deg=round(avg, 1),
        peak_angle_deg=round(peak, 1),
        longest_streak_min=round(longest_run_s / 60.0, 1),
        episodes=episodes,
    )
