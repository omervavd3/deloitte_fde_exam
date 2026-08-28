from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.scoring.profiles import METRICS


class WeightProfileBase(BaseModel):
    label: str = Field(min_length=1, max_length=80)
    description: str = ""
    weights: dict[str, float]

    @field_validator("weights")
    @classmethod
    def validate_weights(cls, v: dict[str, float]) -> dict[str, float]:
        unknown = set(v) - set(METRICS)
        if unknown:
            raise ValueError(f"unknown metrics: {sorted(unknown)}")
        if any(w < 0 for w in v.values()):
            raise ValueError("weights must be non-negative")
        total = sum(v.values())
        if total <= 0:
            raise ValueError("weights must sum to more than zero")
        return {k: round(w / total, 4) for k, w in v.items()}


class WeightProfileCreate(WeightProfileBase):
    name: str = Field(pattern=r"^[a-z0-9_]{3,40}$")


class WeightProfileUpdate(WeightProfileBase):
    pass


class WeightProfile(WeightProfileBase):
    name: str
    is_builtin: bool
    updated_at: datetime
