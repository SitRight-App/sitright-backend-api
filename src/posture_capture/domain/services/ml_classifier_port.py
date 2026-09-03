from typing import Protocol

from ..entities.posture_reading import PostureReading


class MLClassifierPort(Protocol):
    """Outbound port — clasificador ML externo (sitright-ml-service)."""

    async def classify(
        self, reading: PostureReading, reference: dict[str, list[float]] | None = None
    ) -> tuple[str, float]: ...
