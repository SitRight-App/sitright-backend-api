from dataclasses import dataclass


@dataclass(frozen=True)
class RegisterVestCommand:
    mac_address: str
    firmware_version: str = "0.1.0"
