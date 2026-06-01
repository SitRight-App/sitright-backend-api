import secrets
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from ....iam.domain.services.password_service import PasswordService
from ...domain.entities.vest_device import VestDevice
from ...domain.repositories.vest_device_repository import VestDeviceRepository
from ...domain.value_objects.mqtt_credentials import MqttCredentials


@dataclass
class LinkVestCommand:
    mac_address: str
    user_id: UUID
    pairing_code: str


class LinkVestHandler:
    def __init__(
        self,
        repo: VestDeviceRepository,
        password_service: PasswordService,
        expected_pairing_code: str | None = None,
    ) -> None:
        self._repo = repo
        self._password_service = password_service
        self._expected_pairing_code = expected_pairing_code

    async def execute(self, command: LinkVestCommand) -> tuple[VestDevice, str]:
        if self._expected_pairing_code and command.pairing_code != self._expected_pairing_code:
            raise ValueError("Código de emparejamiento inválido")

        mac = command.mac_address.upper().strip()
        device = await self._repo.find_by_mac_address(mac)
        if device is None:
            raise ValueError("Chaleco no registrado")
        if device.is_linked() and device.user_id != command.user_id:
            raise ValueError("El chaleco ya está vinculado a otro usuario")

        username = _generate_mqtt_username(mac)
        plain_password = secrets.token_urlsafe(24)
        creds = MqttCredentials(
            username=username,
            password_hash=self._password_service.hash(plain_password),
            rotated_at=datetime.utcnow(),
        )
        device.link_to_user(command.user_id, creds)
        await self._repo.save(device)
        return device, plain_password


def _generate_mqtt_username(mac: str) -> str:
    return "vest-" + mac.replace(":", "").lower()
