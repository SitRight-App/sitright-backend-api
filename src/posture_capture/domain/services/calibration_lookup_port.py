from typing import Protocol
from uuid import UUID


class CalibrationLookupPort(Protocol):
    """Outbound port — postura neutra (calibración) del usuario, por zona.

    Devuelve {"cervical": [ax, ay, az], "dorsal": [...], "lumbar": [...]} o None
    si el usuario no tiene un chaleco calibrado.
    """

    async def get_reference(self, user_id: UUID) -> dict[str, list[float]] | None: ...
