from dataclasses import dataclass


@dataclass(frozen=True)
class LoginCommand:
    email: str
    plain_password: str


class InvalidCredentialsError(Exception):
    pass


class InactiveAccountError(Exception):
    pass
