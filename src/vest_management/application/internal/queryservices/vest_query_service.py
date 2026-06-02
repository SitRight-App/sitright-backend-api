"""Implementación de IVestQueryService."""
from dataclasses import dataclass

from ....domain.entities.vest_device import VestDevice
from ....domain.model.queries.get_my_vest_query import GetMyVestQuery
from ....domain.model.queries.get_vest_by_mac_query import GetVestByMacQuery
from ....domain.repositories.vest_device_repository import VestDeviceRepository


@dataclass
class VestQueryService:
    vest_device_repository: VestDeviceRepository

    async def handle_get_my_vest(self, query: GetMyVestQuery) -> VestDevice | None:
        return await self.vest_device_repository.find_by_user_id(query.user_id)

    async def handle_get_vest_by_mac(
        self, query: GetVestByMacQuery
    ) -> VestDevice | None:
        return await self.vest_device_repository.find_by_mac_address(query.mac_address)
