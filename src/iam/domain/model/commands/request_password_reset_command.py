from dataclasses import dataclass


@dataclass(frozen=True)
class RequestPasswordResetCommand:
    email: str
