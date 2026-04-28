from dataclasses import dataclass

_ACCEL_RANGE = 16.0


@dataclass(frozen=True)
class SensorData:
    ax: float
    ay: float
    az: float

    def __post_init__(self) -> None:
        for val in (self.ax, self.ay, self.az):
            if not -_ACCEL_RANGE <= val <= _ACCEL_RANGE:
                raise ValueError(
                    f"Valor de aceleración fuera de rango ±{_ACCEL_RANGE}g: {val}"
                )
