"""Implementación del PostureCaptureCommandService."""
import dataclasses
import logging
from dataclasses import dataclass

from ....domain.entities.posture_reading import PostureReading
from ....domain.model.commands.save_reading_command import SaveReadingCommand
from ....domain.repositories.posture_reading_repository import PostureReadingRepository
from ....domain.services.ml_classifier_port import MLClassifierPort
from ....domain.services.posture_capture_command_service import (
    IPostureCaptureCommandService,
)
from ....domain.value_objects.sensor_data import SensorData

logger = logging.getLogger(__name__)


@dataclass
class PostureCaptureCommandService(IPostureCaptureCommandService):
    posture_reading_repository: PostureReadingRepository
    ml_classifier: MLClassifierPort

    async def handle_save_reading(self, command: SaveReadingCommand) -> PostureReading:
        reading = PostureReading(
            id=command.reading_id,
            vest_id=command.vest_id,
            cervical=SensorData(*command.cervical),
            dorsal=SensorData(*command.dorsal),
            lumbar=SensorData(*command.lumbar),
            timestamp=command.timestamp,
            battery_percent=command.battery_percent,
            session_id=command.session_id,
            user_id=command.user_id,
        )

        try:
            posture_class, confidence = await self.ml_classifier.classify(reading)
            reading = dataclasses.replace(
                reading, posture_class=posture_class, confidence=confidence
            )
        except Exception as exc:
            # Si el ml-service no respondió a tiempo (timeout 2 s) u otro
            # error, la lectura queda como 'indeterminate' y se registra el
            # incidente.
            logger.warning(
                "[ml] no se pudo clasificar la lectura %s, queda como indeterminate: %s",
                reading.id,
                exc,
            )

        await self.posture_reading_repository.save(reading)
        return reading
