from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from ..value_objects.calibration_reference import CalibrationReference
from ..value_objects.mqtt_credentials import MqttCredentials


@dataclass
class VestDevice:
    id: UUID
    mac_address: str
    firmware_version: str
    created_at: datetime
    user_id: UUID | None = None
    calibration_reference: CalibrationReference | None = None
    mqtt_credentials: MqttCredentials | None = None
    battery_level: int = 100
    is_active: bool = True
    linked_at: datetime | None = None

    def link_to_user(
        self, user_id: UUID, mqtt_credentials: MqttCredentials
    ) -> None:
        self.user_id = user_id
        self.mqtt_credentials = mqtt_credentials
        self.linked_at = datetime.now(timezone.utc)
        self.is_active = True

    def unlink(self) -> None:
        self.user_id = None
        self.linked_at = None
        self.is_active = False

    def calibrate(self, reference: CalibrationReference) -> None:
        self.calibration_reference = reference

    def update_battery(self, level: int) -> None:
        if not 0 <= level <= 100:
            raise ValueError("battery_level fuera de rango")
        self.battery_level = level

    def is_calibrated(self) -> bool:
        return self.calibration_reference is not None

    def is_linked(self) -> bool:
        return self.user_id is not None
