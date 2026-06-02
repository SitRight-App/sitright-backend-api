from dataclasses import dataclass

from ...value_objects.role import Role


@dataclass(frozen=True)
class RegisterUserCommand:
    name: str
    email: str
    plain_password: str
    role: Role
    weight_kg: float | None = None
    height_cm: float | None = None


class UserAlreadyExistsError(Exception):
    pass
