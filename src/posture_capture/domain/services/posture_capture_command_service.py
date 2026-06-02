"""Interfaz del servicio de comandos para posture_capture.

Cubre el caso de uso de guardar lecturas: clasificar via ML, persistir.
"""
from typing import Protocol

from ..entities.posture_reading import PostureReading
from ..model.commands.save_reading_command import SaveReadingCommand


class IPostureCaptureCommandService(Protocol):
    async def handle_save_reading(self, command: SaveReadingCommand) -> PostureReading: ...
