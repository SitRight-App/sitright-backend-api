from dataclasses import dataclass

from ...domain.entities.vest_device import VestDevice
from ...domain.repositories.vest_device_repository import VestDeviceRepository


@dataclass(frozen=True)
class GetVestByMacQuery:
    mac_address: str


@dataclass
class GetVestByMacHandler:
    repo: VestDeviceRepository

    async def execute(self, query: GetVestByMacQuery) -> VestDevice | None:
        return await self.repo.find_by_mac_address(query.mac_address)
