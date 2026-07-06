from datetime import datetime
from uuid import UUID

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....shared.datetime_utils import parse_utc

from ....posture_capture.domain.value_objects.sensor_data import SensorData
from ...domain.entities.vest_device import VestDevice
from ...domain.value_objects.calibration_reference import CalibrationReference
from ...domain.value_objects.mqtt_credentials import MqttCredentials


class MongoVestDeviceRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db["vest_devices"]

    async def save(self, device: VestDevice) -> None:
        await self._col.replace_one(
            {"_id": str(device.id)},
            self._to_document(device),
            upsert=True,
        )

    async def find_by_id(self, device_id: UUID) -> VestDevice | None:
        doc = await self._col.find_one({"_id": str(device_id)})
        return self._from_document(doc) if doc else None

    async def find_by_mac_address(self, mac: str) -> VestDevice | None:
        doc = await self._col.find_one({"mac_address": mac.upper().strip()})
        return self._from_document(doc) if doc else None

    async def find_by_user_id(self, user_id: UUID) -> VestDevice | None:
        doc = await self._col.find_one({"user_id": str(user_id), "is_active": True})
        return self._from_document(doc) if doc else None

    async def find_by_mqtt_username(self, username: str) -> VestDevice | None:
        doc = await self._col.find_one({"mqtt_credentials.username": username})
        return self._from_document(doc) if doc else None

    async def exists_by_mac_address(self, mac: str) -> bool:
        count = await self._col.count_documents(
            {"mac_address": mac.upper().strip()}, limit=1
        )
        return count > 0

    def _to_document(self, d: VestDevice) -> dict:
        return {
            "_id": str(d.id),
            "mac_address": d.mac_address,
            "user_id": str(d.user_id) if d.user_id else None,
            "firmware_version": d.firmware_version,
            "battery_level": d.battery_level,
            "is_active": d.is_active,
            "linked_at": d.linked_at.isoformat() if d.linked_at else None,
            "created_at": d.created_at.isoformat(),
            "calibration_reference": (
                {
                    "cervical": {"ax": d.calibration_reference.cervical.ax, "ay": d.calibration_reference.cervical.ay, "az": d.calibration_reference.cervical.az},
                    "dorsal": {"ax": d.calibration_reference.dorsal.ax, "ay": d.calibration_reference.dorsal.ay, "az": d.calibration_reference.dorsal.az},
                    "lumbar": {"ax": d.calibration_reference.lumbar.ax, "ay": d.calibration_reference.lumbar.ay, "az": d.calibration_reference.lumbar.az},
                    "calibrated_at": d.calibration_reference.calibrated_at.isoformat(),
                }
                if d.calibration_reference
                else None
            ),
            "mqtt_credentials": (
                {
                    "username": d.mqtt_credentials.username,
                    "password_hash": d.mqtt_credentials.password_hash,
                    "rotated_at": d.mqtt_credentials.rotated_at.isoformat(),
                }
                if d.mqtt_credentials
                else None
            ),
        }

    def _from_document(self, doc: dict) -> VestDevice:
        cal = doc.get("calibration_reference")
        calibration = None
        if cal:
            calibration = CalibrationReference(
                cervical=SensorData(cal["cervical"]["ax"], cal["cervical"]["ay"], cal["cervical"]["az"]),
                dorsal=SensorData(cal["dorsal"]["ax"], cal["dorsal"]["ay"], cal["dorsal"]["az"]),
                lumbar=SensorData(cal["lumbar"]["ax"], cal["lumbar"]["ay"], cal["lumbar"]["az"]),
                calibrated_at=parse_utc(cal["calibrated_at"]),
            )

        creds = doc.get("mqtt_credentials")
        mqtt_creds = None
        if creds:
            mqtt_creds = MqttCredentials(
                username=creds["username"],
                password_hash=creds["password_hash"],
                rotated_at=parse_utc(creds["rotated_at"]),
            )

        return VestDevice(
            id=UUID(doc["_id"]),
            mac_address=doc["mac_address"],
            user_id=UUID(doc["user_id"]) if doc.get("user_id") else None,
            firmware_version=doc.get("firmware_version", "0.1.0"),
            battery_level=doc.get("battery_level", 100),
            is_active=doc.get("is_active", True),
            linked_at=parse_utc(doc["linked_at"]) if doc.get("linked_at") else None,
            created_at=parse_utc(doc["created_at"]),
            calibration_reference=calibration,
            mqtt_credentials=mqtt_creds,
        )
