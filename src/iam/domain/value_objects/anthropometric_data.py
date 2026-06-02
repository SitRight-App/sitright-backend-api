from dataclasses import dataclass

# HU-26 AC2 — rangos antropométricos razonables. Fuera de estos rangos no
# se trata de un valor humano realista; el handler debe rechazar la
# actualización con error de validación.
HEIGHT_MIN_CM = 100.0
HEIGHT_MAX_CM = 250.0
WEIGHT_MIN_KG = 25.0
WEIGHT_MAX_KG = 300.0


@dataclass(frozen=True)
class AnthropometricData:
    weight_kg: float | None = None
    height_cm: float | None = None

    def __post_init__(self) -> None:
        if self.height_cm is not None and not (HEIGHT_MIN_CM <= self.height_cm <= HEIGHT_MAX_CM):
            raise ValueError(
                f"La estatura debe estar entre {HEIGHT_MIN_CM:.0f} y {HEIGHT_MAX_CM:.0f} cm"
            )
        if self.weight_kg is not None and not (WEIGHT_MIN_KG <= self.weight_kg <= WEIGHT_MAX_KG):
            raise ValueError(
                f"El peso debe estar entre {WEIGHT_MIN_KG:.0f} y {WEIGHT_MAX_KG:.0f} kg"
            )
