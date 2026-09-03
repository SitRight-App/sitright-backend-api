from uuid import UUID

from ....vest_management.domain.model.queries.get_my_vest_query import GetMyVestQuery
from ....vest_management.domain.services.vest_query_service import IVestQueryService


class VestCalibrationLookup:
    """Obtiene la calibración del chaleco vinculado al usuario (vest_management)."""

    def __init__(self, vest_query_service: IVestQueryService) -> None:
        self._vests = vest_query_service

    async def get_reference(self, user_id: UUID) -> dict[str, list[float]] | None:
        vest = await self._vests.handle_get_my_vest(GetMyVestQuery(user_id=user_id))
        if vest is None or vest.calibration_reference is None:
            return None
        ref = vest.calibration_reference
        return {
            "cervical": [ref.cervical.ax, ref.cervical.ay, ref.cervical.az],
            "dorsal": [ref.dorsal.ax, ref.dorsal.ay, ref.dorsal.az],
            "lumbar": [ref.lumbar.ax, ref.lumbar.ay, ref.lumbar.az],
        }
