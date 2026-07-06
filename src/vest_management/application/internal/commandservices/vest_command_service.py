"""Implementación de IVestCommandService — agrupa todos los casos de uso de
escritura del bounded context vest_management.
"""
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from .....iam.domain.services.password_service import PasswordService
from ....domain.entities.vest_device import VestDevice
from ....domain.model.commands.calibrate_vest_command import CalibrateVestCommand
from ....domain.model.commands.link_vest_command import LinkVestCommand
from ....domain.model.commands.register_vest_command import RegisterVestCommand
from ....domain.model.commands.send_vest_command_command import SendVestCommand
from ....domain.model.commands.unlink_vest_command import UnlinkVestCommand
from ....domain.repositories.vest_device_repository import VestDeviceRepository
from ....domain.services.vest_command_publisher import VestCommandPublisher
from ....domain.services.vest_command_service import IVestCommandService
from ....domain.value_objects.calibration_reference import CalibrationReference
from ....domain.value_objects.mqtt_credentials import MqttCredentials
from .....posture_capture.domain.value_objects.sensor_data import SensorData


def _is_valid_mac(mac: str) -> bool:
    parts = mac.split(":")
    if len(parts) != 6:
        return False
    return all(len(p) == 2 and all(c in "0123456789ABCDEF" for c in p) for p in parts)


def _generate_mqtt_username(mac: str) -> str:
    return "vest-" + mac.replace(":", "").lower()


@dataclass
class VestCommandService(IVestCommandService):
    vest_device_repository: VestDeviceRepository
    password_service: PasswordService
    vest_command_publisher: VestCommandPublisher | None = None
    expected_pairing_code: str | None = None

    async def handle_register_vest(self, command: RegisterVestCommand) -> VestDevice:
        mac = command.mac_address.upper().strip()
        if not _is_valid_mac(mac):
            raise ValueError("MAC address inválida")
        if await self.vest_device_repository.exists_by_mac_address(mac):
            raise ValueError("Ya existe un chaleco con esa MAC")

        device = VestDevice(
            id=uuid4(),
            mac_address=mac,
            firmware_version=command.firmware_version,
            created_at=datetime.now(timezone.utc),
            is_active=False,
        )
        await self.vest_device_repository.save(device)
        return device

    async def handle_link_vest(
        self, command: LinkVestCommand
    ) -> tuple[VestDevice, str]:
        if (
            self.expected_pairing_code
            and command.pairing_code != self.expected_pairing_code
        ):
            raise ValueError("Código de emparejamiento inválido")

        mac = command.mac_address.upper().strip()
        device = await self.vest_device_repository.find_by_mac_address(mac)
        if device is None:
            raise ValueError("Chaleco no registrado")
        if device.is_linked() and device.user_id != command.user_id:
            raise ValueError("El chaleco ya está vinculado a otro usuario")

        username = _generate_mqtt_username(mac)
        plain_password = secrets.token_urlsafe(24)
        creds = MqttCredentials(
            username=username,
            password_hash=self.password_service.hash(plain_password),
            rotated_at=datetime.now(timezone.utc),
        )
        device.link_to_user(command.user_id, creds)
        await self.vest_device_repository.save(device)
        return device, plain_password

    async def handle_calibrate_vest(
        self, command: CalibrateVestCommand
    ) -> VestDevice:
        device = await self.vest_device_repository.find_by_id(command.device_id)
        if device is None:
            raise ValueError("Chaleco no encontrado")
        if not device.is_linked():
            raise ValueError("Solo se puede calibrar un chaleco vinculado")

        reference = CalibrationReference(
            cervical=SensorData(*command.cervical),
            dorsal=SensorData(*command.dorsal),
            lumbar=SensorData(*command.lumbar),
            calibrated_at=datetime.now(timezone.utc),
        )
        device.calibrate(reference)
        await self.vest_device_repository.save(device)
        return device

    async def handle_unlink_vest(self, command: UnlinkVestCommand) -> VestDevice:
        device = await self.vest_device_repository.find_by_id(command.vest_id)
        if device is None:
            raise ValueError("Chaleco no encontrado")
        if device.user_id != command.user_id:
            raise ValueError("El chaleco no pertenece al usuario actual")
        device.unlink()
        await self.vest_device_repository.save(device)
        return device

    async def handle_send_vest_command(self, command: SendVestCommand) -> None:
        if self.vest_command_publisher is None:
            raise ValueError(
                "El publisher MQTT no está habilitado; configura MQTT_ENABLED=true"
            )

        device = await self.vest_device_repository.find_by_id(command.device_id)
        if device is None:
            raise ValueError("Chaleco no encontrado")
        if not device.is_linked():
            raise ValueError("Solo se puede enviar comandos a un chaleco vinculado")

        mac = device.mac_address
        if command.command_type == "recalibrate":
            await self.vest_command_publisher.publish_recalibrate(mac)
        elif command.command_type == "restart":
            await self.vest_command_publisher.publish_restart(mac)
        elif command.command_type == "firmware_update":
            if not command.firmware_version:
                raise ValueError("firmware_version requerido para firmware_update")
            await self.vest_command_publisher.publish_firmware_update(
                mac, command.firmware_version
            )
        else:
            raise ValueError(f"Comando desconocido: {command.command_type}")
