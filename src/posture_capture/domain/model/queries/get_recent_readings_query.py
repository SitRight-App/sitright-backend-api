from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class GetRecentReadingsQuery:
    """Parámetros de la consulta de lecturas recientes para el timeline.

    - `minutes` y `(since, until)` son mutuamente excluyentes; si se pasan
      `since`/`until` se ignora `minutes`.
    - `vest_id` filtra a las lecturas del chaleco del usuario actual.
    """

    limit: int = 60
    minutes: int | None = None
    since: datetime | None = None
    until: datetime | None = None
    vest_id: str | None = None
