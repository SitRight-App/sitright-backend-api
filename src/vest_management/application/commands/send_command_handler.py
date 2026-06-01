from dataclasses import dataclass
from uuid import UUID

from ...domain.repositories.vest_device_repository import VestDeviceRepository
from ...domain.services.vest_command_publisher import VestCommandPublisher


@dataclass
class SendVestCommand:
    device_id: UUID
    command_type: str  # "recalibrate" | "restart" | "firmware_update"
    firmware_version: str | None = None


class SendVestCommandHandler:
    def __init__(
        self,
        repo: VestDeviceRepository,
        publisher: VestCommandPublisher,
    ) -> None:
        self._repo = repo
        self._publisher = publisher

    async def execute(self, command: SendVestCommand) -> None:
        device = await self._repo.find_by_id(command.device_id)
        if device is None:
            raise ValueError("Chaleco no encontrado")
        if not device.is_linked():
            raise ValueError("Solo se puede enviar comandos a un chaleco vinculado")

        mac = device.mac_address
        if command.command_type == "recalibrate":
            await self._publisher.publish_recalibrate(mac)
        elif command.command_type == "restart":
            await self._publisher.publish_restart(mac)
        elif command.command_type == "firmware_update":
            if not command.firmware_version:
                raise ValueError("firmware_version requerido para firmware_update")
            await self._publisher.publish_firmware_update(mac, command.firmware_version)
        else:
            raise ValueError(f"Comando desconocido: {command.command_type}")
