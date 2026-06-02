from dataclasses import dataclass


@dataclass(frozen=True)
class GetLatestReadingQuery:
    """Última lectura del chaleco vinculado al usuario.

    El service resuelve el vest_id contra vest_management antes de consultar.
    """

    vest_id: str | None = None
