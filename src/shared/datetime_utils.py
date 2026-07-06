"""Utilidades de fecha/hora: todo el sistema trabaja en UTC con zona explícita.

Al leer marcas persistidas, algunas antiguas se guardaron sin zona (naive); se
asumen en UTC para que nunca se mezclen datetimes aware y naive en la aritmética
ni se serialicen sin el desplazamiento de zona.
"""
from datetime import datetime, timezone


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_utc(value: str) -> datetime:
    return ensure_utc(datetime.fromisoformat(value))
