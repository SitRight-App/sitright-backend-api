from dataclasses import dataclass


@dataclass(frozen=True)
class AnthropometricData:
    weight_kg: float | None = None
    height_cm: float | None = None
