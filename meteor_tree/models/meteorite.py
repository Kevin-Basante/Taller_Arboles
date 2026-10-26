"""Domain model: a catalogued meteorite."""

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, Dict

GROUPS = ("Iron", "Stony", "Stony-iron", "Martian", "Lunar")
RECOVERY_TYPES = ("Fell", "Found")


@dataclass
class Meteorite:
    name: str
    mass_kg: float
    country: str
    year: int
    group: str
    classification: str
    recovery: str

    def __post_init__(self) -> None:
        self.name = str(self.name).strip()
        self.country = str(self.country).strip()
        self.classification = str(self.classification).strip()
        self.mass_kg = round(float(self.mass_kg), 3)
        self.year = int(self.year)
        self.validate()

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Name is required")
        if not self.country:
            raise ValueError("Country is required")
        if self.mass_kg <= 0:
            raise ValueError("Mass must be greater than zero")
        if not 800 <= self.year <= date.today().year:
            raise ValueError("Year must be between 800 and the current year")
        if self.group not in GROUPS:
            raise ValueError(f"Group must be one of: {', '.join(GROUPS)}")
        if self.recovery not in RECOVERY_TYPES:
            raise ValueError("Recovery must be 'Fell' or 'Found'")

    @property
    def key(self) -> float:
        """The tree is ordered by mass in kilograms."""
        return self.mass_kg

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "Meteorite":
        try:
            return cls(
                name=payload["name"],
                mass_kg=payload["mass_kg"],
                country=payload["country"],
                year=payload["year"],
                group=payload["group"],
                classification=payload.get("classification", ""),
                recovery=payload["recovery"],
            )
        except KeyError as missing:
            raise ValueError(f"Missing field: {missing.args[0]}") from None
        except (TypeError,) as error:
            raise ValueError(str(error)) from None
