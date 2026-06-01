from datetime import datetime

from pydantic import BaseModel, Field


class RegisterVestRequest(BaseModel):
    mac_address: str
    firmware_version: str = "0.1.0"


class LinkVestRequest(BaseModel):
    mac_address: str
    pairing_code: str


class SensorReadingTuple(BaseModel):
    ax: float
    ay: float
    az: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.ax, self.ay, self.az)


class CalibrateVestRequest(BaseModel):
    cervical: SensorReadingTuple
    dorsal: SensorReadingTuple
    lumbar: SensorReadingTuple


class SendCommandRequest(BaseModel):
    command_type: str = Field(..., description="recalibrate | restart | firmware_update")
    firmware_version: str | None = None


class VestResponse(BaseModel):
    id: str
    mac_address: str
    user_id: str | None
    firmware_version: str
    battery_level: int
    is_active: bool
    is_calibrated: bool
    is_linked: bool
    linked_at: datetime | None
    created_at: datetime


class LinkVestResponse(BaseModel):
    vest: VestResponse
    mqtt_username: str
    mqtt_password: str  # plain text, devuelto solo en este momento
