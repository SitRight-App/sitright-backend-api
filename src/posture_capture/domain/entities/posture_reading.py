from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ..value_objects.sensor_data import SensorData


@dataclass(frozen=True)
class PostureReading:
    id: UUID
    vest_id: str
    cervical: SensorData
    dorsal: SensorData
    lumbar: SensorData
    timestamp: datetime
    posture_class: str = "indeterminate"
    confidence: float = 0.0
    battery_percent: int = 100
    # Sesión a la que pertenece la lectura (si había una activa al capturarla).
    # Clave estable para agrupar las lecturas de una sesión: no depende del
    # formato del vest_id ni de comparar rangos horarios frágiles.
    session_id: UUID | None = None
    # Usuario dueño del chaleco al capturar la lectura.
    user_id: UUID | None = None
