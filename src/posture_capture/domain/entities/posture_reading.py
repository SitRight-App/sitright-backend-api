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
