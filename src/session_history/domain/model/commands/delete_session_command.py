from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DeleteSessionCommand:
    session_id: UUID
    # Dueño esperado: el borrado solo procede si la sesión le pertenece.
    user_id: UUID
