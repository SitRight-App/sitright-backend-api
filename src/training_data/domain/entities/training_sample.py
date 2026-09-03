from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ....posture_capture.domain.value_objects.sensor_data import SensorData


@dataclass(frozen=True)
class TrainingSample:
    """Muestra etiquetada capturada para entrenar el clasificador (Ruta B)."""

    id: UUID
    subject: str  # identificador anonimizado del participante
    label: str  # adequate | forward_slouch | excessive_recline | neutral
    cervical: SensorData
    dorsal: SensorData
    lumbar: SensorData
    captured_at: datetime
    created_by: UUID  # cuenta (admin) que realizó la captura
