from dataclasses import dataclass
from uuid import UUID

from ...domain.entities.vest_device import VestDevice
from ...domain.repositories.vest_device_repository import VestDeviceRepository


@dataclass
class GetMyVestQuery:
    user_id: UUID


class GetMyVestHandler:
    def __init__(self, repo: VestDeviceRepository) -> None:
        self._repo = repo

    async def execute(self, query: GetMyVestQuery) -> VestDevice | None:
        return await self._repo.find_by_user_id(query.user_id)
