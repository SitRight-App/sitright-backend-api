import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Protocol
from uuid import UUID, uuid4

from asyncio_mqtt import Client as MqttClient, MqttError

from ....shared.datetime_utils import parse_utc

from ...domain.model.commands.save_reading_command import SaveReadingCommand
from ...domain.services.posture_capture_command_service import (
    IPostureCaptureCommandService,
)

logger = logging.getLogger(__name__)


class VestLookupPort(Protocol):
    """Resuelve user_id y vest_id a partir de la MAC del topic."""

    async def resolve(self, mac_address: str) -> tuple[UUID, UUID] | None: ...


class SessionStarterPort(Protocol):
    """Garantiza que exista una sesión activa antes de aceptar la lectura."""

    async def ensure_active(self, user_id: UUID, vest_device_id: UUID) -> UUID: ...


class PostureCaptureMqttSubscriber:
    """Suscriptor MQTT al topic sitright/devices/+/readings.

    Cada mensaje recibido se mapea a un SaveReadingCommand y se delega al
    PostureCaptureCommandService (mismo caso de uso que el endpoint REST).
    """

    def __init__(
        self,
        mqtt_client: MqttClient,
        command_service: IPostureCaptureCommandService,
        vest_lookup: VestLookupPort,
        session_starter: SessionStarterPort,
        topic_pattern: str = "sitright/devices/+/readings",
    ) -> None:
        self._client = mqtt_client
        self._command_service = command_service
        self._vest_lookup = vest_lookup
        self._session_starter = session_starter
        self._topic_pattern = topic_pattern
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        await self._client.subscribe(self._topic_pattern)
        self._task = asyncio.create_task(self._listen())
        logger.info("MQTT subscriber escuchando en %s", self._topic_pattern)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _listen(self) -> None:
        async with self._client.messages() as messages:
            async for message in messages:
                try:
                    await self._on_message(str(message.topic), message.payload)
                except Exception:
                    logger.exception("Error procesando mensaje MQTT")

    async def _on_message(self, topic: str, payload: bytes) -> None:
        mac = self._extract_mac(topic)
        if not mac:
            logger.warning("Topic sin MAC: %s", topic)
            return

        resolved = await self._vest_lookup.resolve(mac)
        if resolved is None:
            logger.warning("Chaleco MAC %s no vinculado, descarto lectura", mac)
            return
        user_id, vest_id = resolved

        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("Payload no es JSON válido: %s", payload[:80])
            return

        session_id = await self._session_starter.ensure_active(user_id, vest_id)

        timestamp_str = data.get("timestamp")
        timestamp = (
            parse_utc(timestamp_str) if timestamp_str else datetime.now(timezone.utc)
        )

        command = SaveReadingCommand(
            reading_id=uuid4(),
            vest_id=str(vest_id),
            user_id=user_id,
            cervical=_triple(data.get("cervical")),
            dorsal=_triple(data.get("dorsal")),
            lumbar=_triple(data.get("lumbar")),
            timestamp=timestamp,
            battery_percent=int(data.get("battery_percent", 100)),
            session_id=session_id,
        )
        await self._command_service.handle_save_reading(command)

    @staticmethod
    def _extract_mac(topic: str) -> str | None:
        # topic: sitright/devices/{mac}/readings
        parts = topic.split("/")
        if len(parts) == 4 and parts[0] == "sitright" and parts[1] == "devices":
            return parts[2].upper()
        return None


def _triple(value) -> tuple[float, float, float]:
    if isinstance(value, dict):
        return (float(value["ax"]), float(value["ay"]), float(value["az"]))
    if isinstance(value, (list, tuple)) and len(value) == 3:
        return (float(value[0]), float(value[1]), float(value[2]))
    raise ValueError(f"Sensor data inválida: {value}")
