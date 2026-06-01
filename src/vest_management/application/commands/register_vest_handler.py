from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

from ...domain.entities.vest_device import VestDevice
from ...domain.repositories.vest_device_repository import VestDeviceRepository


@dataclass
class RegisterVestCommand:
    mac_address: str
    firmware_version: str = "0.1.0"


class RegisterVestHandler:
    def __init__(self, repo: VestDeviceRepository) -> None:
        self._repo = repo

    async def execute(self, command: RegisterVestCommand) -> VestDevice:
        mac = command.mac_address.upper().strip()
        if not _is_valid_mac(mac):
            raise ValueError("MAC address inválida")
        if await self._repo.exists_by_mac_address(mac):
            raise ValueError("Ya existe un chaleco con esa MAC")

        device = VestDevice(
            id=uuid4(),
            mac_address=mac,
            firmware_version=command.firmware_version,
            created_at=datetime.utcnow(),
            is_active=False,
        )
        await self._repo.save(device)
        return device


def _is_valid_mac(mac: str) -> bool:
    parts = mac.split(":")
    if len(parts) != 6:
        return False
    return all(len(p) == 2 and all(c in "0123456789ABCDEF" for c in p) for p in parts)
