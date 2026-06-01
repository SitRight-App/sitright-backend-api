import logging

from asyncio_mqtt import Client as MqttClient, TLSParameters
import ssl

from .config import settings

logger = logging.getLogger(__name__)


_client: MqttClient | None = None


def _build_client() -> MqttClient:
    if not settings.mqtt_host:
        raise RuntimeError("MQTT_HOST no configurado")

    tls_params: TLSParameters | None = None
    if settings.mqtt_use_tls:
        tls_params = TLSParameters(
            ca_certs=None,
            certfile=None,
            keyfile=None,
            cert_reqs=ssl.CERT_REQUIRED,
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )

    return MqttClient(
        hostname=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_username or None,
        password=settings.mqtt_password or None,
        tls_params=tls_params,
        client_id=settings.mqtt_client_id,
        keepalive=60,
    )


async def connect_mqtt() -> MqttClient:
    global _client
    if _client is None:
        _client = _build_client()
    await _client.__aenter__()
    logger.info(
        "MQTT conectado a %s:%s (TLS=%s)",
        settings.mqtt_host,
        settings.mqtt_port,
        settings.mqtt_use_tls,
    )
    return _client


async def disconnect_mqtt() -> None:
    global _client
    if _client is not None:
        await _client.__aexit__(None, None, None)
        _client = None
        logger.info("MQTT desconectado")


def get_mqtt_client() -> MqttClient:
    if _client is None:
        raise RuntimeError("MQTT client no inicializado")
    return _client
