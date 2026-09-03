from typing import Protocol

from ..entities.training_sample import TrainingSample


class TrainingSampleRepository(Protocol):
    async def save_many(self, samples: list[TrainingSample]) -> None: ...

    async def list_all(self) -> list[TrainingSample]: ...

    async def counts(self) -> dict: ...
