from dataclasses import dataclass, field


@dataclass(frozen=True)
class SessionSummary:
    total_readings: int
    valid_readings: int
    adequate_percentage: float
    dominant_deviation: str | None
    total_minutes: float
    counts_by_class: dict[str, int] = field(default_factory=dict)
