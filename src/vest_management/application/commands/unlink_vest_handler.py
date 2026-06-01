from dataclasses import dataclass
from uuid import UUID

from ...domain.entities.vest_device import VestDevice
from ...domain.repositories.vest_device_repository import VestDeviceRepository


@dataclass(frozen=True)
class UnlinkVestCommand:
    vest_id: UUID
    user_id: UUID


@dataclass
class UnlinkVestHandler:
    repo: VestDeviceRepository

    async def execute(self, command: UnlinkVestCommand) -> VestDevice:
        vest = await self.repo.find_by_id(command.vest_id)
        if vest is None:
            raise ValueError("Chaleco no encontrado")
        if vest.user_id != command.user_id:
            raise ValueError("El chaleco no pertenece al usuario actual")
        vest.unlink()
        await self.repo.save(vest)
        return vest
