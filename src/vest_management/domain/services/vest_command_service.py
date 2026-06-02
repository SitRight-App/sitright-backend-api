"""Interfaz del servicio de comandos para vest_management."""
from typing import Protocol

from ..entities.vest_device import VestDevice
from ..model.commands.calibrate_vest_command import CalibrateVestCommand
from ..model.commands.link_vest_command import LinkVestCommand
from ..model.commands.register_vest_command import RegisterVestCommand
from ..model.commands.send_vest_command_command import SendVestCommand
from ..model.commands.unlink_vest_command import UnlinkVestCommand


class IVestCommandService(Protocol):
    async def handle_register_vest(self, command: RegisterVestCommand) -> VestDevice: ...
    async def handle_link_vest(
        self, command: LinkVestCommand
    ) -> tuple[VestDevice, str]: ...
    async def handle_calibrate_vest(self, command: CalibrateVestCommand) -> VestDevice: ...
    async def handle_unlink_vest(self, command: UnlinkVestCommand) -> VestDevice: ...
    async def handle_send_vest_command(self, command: SendVestCommand) -> None: ...
