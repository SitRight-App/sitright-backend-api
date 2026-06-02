"""Interfaz del servicio de comandos para session_history."""
from typing import Protocol

from ..entities.posture_session import PostureSession
from ..model.commands.close_session_command import CloseSessionCommand
from ..model.commands.start_session_command import StartSessionCommand


class ISessionCommandService(Protocol):
    async def handle_start_session(self, command: StartSessionCommand) -> PostureSession: ...
    async def handle_close_session(self, command: CloseSessionCommand) -> PostureSession: ...
