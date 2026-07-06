"""Analizador de desviación por zona sobre Mongo (ADR-006).

Cruza el bounded context en modo lectura (igual que MongoReadingsAggregator):
lee las lecturas crudas de `posture_readings` por `session_id`, y la referencia
de calibración de `vest_devices`. Calcula la desviación de cada zona de forma
geométrica, independiente de la clase del modelo ML.
"""
from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....shared.datetime_utils import parse_utc

from ....posture_capture.domain.value_objects.sensor_data import SensorData
from ...domain.services.zone_analysis_math import (
    DEFAULT_ZONE_THRESHOLDS_DEG,
    aggregate_zone,
    deviation_angle_deg,
)
from ...domain.value_objects.zone_analysis import SessionZoneAnalysis, ZoneDeviation

ZONES = ("cervical", "dorsal", "lumbar")
# Tope de lecturas a leer por sesión (≈9 h a 5 s = ~6500); evita cargar de más.
_MAX_READINGS = 7000


def _empty_zone() -> ZoneDeviation:
    return ZoneDeviation(0.0, 0.0, 0.0, 0.0, 0.0, 0)


class MongoZoneAnalyzer:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._readings = db["posture_readings"]
        self._vests = db["vest_devices"]

    async def analyze(
        self, session_id: UUID, vest_device_id: UUID
    ) -> SessionZoneAnalysis:
        vest = await self._vests.find_one({"_id": str(vest_device_id)})
        cal = vest.get("calibration_reference") if vest else None
        threshold = DEFAULT_ZONE_THRESHOLDS_DEG["cervical"]

        # Sin calibración no hay neutro: no se puede medir ángulo de forma honesta.
        if not cal:
            return SessionZoneAnalysis(
                calibrated=False,
                threshold_degrees=threshold,
                total_readings=0,
                zones={z: _empty_zone() for z in ZONES},
            )

        neutrals = {
            z: SensorData(cal[z]["ax"], cal[z]["ay"], cal[z]["az"]) for z in ZONES
        }

        # Lecturas de la sesión por session_id (clave estable, ADR-006).
        cursor = (
            self._readings.find({"session_id": str(session_id)})
            .sort("timestamp", 1)
            .limit(_MAX_READINGS)
        )

        times: list[datetime] = []
        samples: dict[str, list[SensorData]] = {z: [] for z in ZONES}
        async for doc in cursor:
            ts_raw = doc.get("timestamp")
            try:
                ts = parse_utc(ts_raw)
            except (TypeError, ValueError):
                continue
            times.append(ts)
            for z in ZONES:
                d = doc.get(z) or {}
                samples[z].append(
                    SensorData(d.get("ax", 0.0), d.get("ay", 0.0), d.get("az", 0.0))
                )

        zones: dict[str, ZoneDeviation] = {}
        for z in ZONES:
            thr = DEFAULT_ZONE_THRESHOLDS_DEG[z]
            angles = [deviation_angle_deg(v, neutrals[z]) for v in samples[z]]
            zones[z] = aggregate_zone(times, angles, thr)

        return SessionZoneAnalysis(
            calibrated=True,
            threshold_degrees=threshold,
            total_readings=len(times),
            zones=zones,
        )
