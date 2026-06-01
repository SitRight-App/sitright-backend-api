from dataclasses import dataclass
from datetime import datetime

from ....posture_capture.domain.value_objects.sensor_data import SensorData


@dataclass(frozen=True)
class CalibrationReference:
    cervical: SensorData
    dorsal: SensorData
    lumbar: SensorData
    calibrated_at: datetime
