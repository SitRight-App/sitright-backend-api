import json
from datetime import datetime, timezone

from asyncio_mqtt import Client as MqttClient


class MqttVestCommandPublisher:
    def __init__(self, mqtt_client: MqttClient, topic_prefix: str = "sitright/devices") -> None:
        self._client = mqtt_client
        self._topic_prefix = topic_prefix

    async def publish_recalibrate(self, mac_address: str) -> None:
        await self._publish(mac_address, {"type": "recalibrate"})

    async def publish_restart(self, mac_address: str) -> None:
        await self._publish(mac_address, {"type": "restart"})

    async def publish_firmware_update(self, mac_address: str, version: str) -> None:
        await self._publish(mac_address, {"type": "firmware_update", "version": version})

    async def _publish(self, mac_address: str, payload: dict) -> None:
        topic = f"{self._topic_prefix}/{mac_address}/commands"
        payload_with_meta = {
            **payload,
            "issued_at": datetime.now(timezone.utc).isoformat(),
        }
        await self._client.publish(topic, json.dumps(payload_with_meta).encode("utf-8"), qos=1)
