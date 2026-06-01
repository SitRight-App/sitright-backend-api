import dataclasses
import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ...domain.entities.posture_reading import PostureReading
from ...domain.repositories.posture_reading_repository import PostureReadingRepository
from ...domain.value_objects.sensor_data import SensorData

logger = logging.getLogger(__name__)


@dataclass
class SaveReadingCommand:
    reading_id: UUID
    vest_id: str
    cervical: tuple[float, float, float]
    dorsal: tuple[float, float, float]
    lumbar: tuple[float, float, float]
    timestamp: datetime
    battery_percent: int = 100


class MLClassifierPort:
    async def classify(self, reading: PostureReading) -> tuple[str, float]: ...


class SaveReadingHandler:
    def __init__(
        self,
        repo: PostureReadingRepository,
        ml_client: MLClassifierPort,
    ) -> None:
        self._repo = repo
        self._ml_client = ml_client

    async def execute(self, command: SaveReadingCommand) -> PostureReading:
        reading = PostureReading(
            id=command.reading_id,
            vest_id=command.vest_id,
            cervical=SensorData(*command.cervical),
            dorsal=SensorData(*command.dorsal),
            lumbar=SensorData(*command.lumbar),
            timestamp=command.timestamp,
            battery_percent=command.battery_percent,
        )

        try:
            posture_class, confidence = await self._ml_client.classify(reading)
            reading = dataclasses.replace(
                reading, posture_class=posture_class, confidence=confidence
            )
        except Exception as exc:
            # HU-04 AC4 — el ml-service no respondió a tiempo (timeout 2s)
            # u otro error: la lectura queda como 'indeterminate' y se registra
            # el incidente para revisión.
            logger.warning(
                "[ml] no se pudo clasificar la lectura %s, queda como indeterminate: %s",
                reading.id,
                exc,
            )

        await self._repo.save(reading)
        return reading
