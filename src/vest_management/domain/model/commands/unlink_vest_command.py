from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class UnlinkVestCommand:
    vest_id: UUID
    user_id: UUID
