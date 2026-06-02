"""Interfaz del servicio de queries para vest_management."""
from typing import Protocol

from ..entities.vest_device import VestDevice
from ..model.queries.get_my_vest_query import GetMyVestQuery
from ..model.queries.get_vest_by_mac_query import GetVestByMacQuery


class IVestQueryService(Protocol):
    async def handle_get_my_vest(self, query: GetMyVestQuery) -> VestDevice | None: ...
    async def handle_get_vest_by_mac(
        self, query: GetVestByMacQuery
    ) -> VestDevice | None: ...
