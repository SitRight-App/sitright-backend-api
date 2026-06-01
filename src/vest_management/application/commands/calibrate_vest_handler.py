from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ....posture_capture.domain.value_objects.sensor_data import SensorData
from ...domain.entities.vest_device import VestDevice
from ...domain.repositories.vest_device_repository import VestDeviceRepository
from ...domain.value_objects.calibration_reference import CalibrationReference


@dataclass
class CalibrateVestCommand:
    device_id: UUID
    cervical: tuple[float, float, float]
    dorsal: tuple[float, float, float]
    lumbar: tuple[float, float, float]


class CalibrateVestHandler:
    def __init__(self, repo: VestDeviceRepository) -> None:
        self._repo = repo

    async def execute(self, command: CalibrateVestCommand) -> VestDevice:
        device = await self._repo.find_by_id(command.device_id)
        if device is None:
            raise ValueError("Chaleco no encontrado")
        if not device.is_linked():
            raise ValueError("Solo se puede calibrar un chaleco vinculado")

        reference = CalibrationReference(
            cervical=SensorData(*command.cervical),
            dorsal=SensorData(*command.dorsal),
            lumbar=SensorData(*command.lumbar),
            calibrated_at=datetime.utcnow(),
        )
        device.calibrate(reference)
        await self._repo.save(device)
        return device
