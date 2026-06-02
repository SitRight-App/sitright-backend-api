from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CalibrateVestCommand:
    device_id: UUID
    cervical: tuple[float, float, float]
    dorsal: tuple[float, float, float]
    lumbar: tuple[float, float, float]
