from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from .config import settings

_client: AsyncIOMotorClient | None = None


def get_database() -> AsyncIOMotorDatabase:
    if _client is None:
        raise RuntimeError("Database not connected. Call connect_database() first.")
    return _client[settings.mongo_db_name]


async def connect_database() -> None:
    global _client
    _client = AsyncIOMotorClient(settings.mongo_uri)


async def disconnect_database() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None
