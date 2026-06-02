from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LinkVestCommand:
    mac_address: str
    user_id: UUID
    pairing_code: str
