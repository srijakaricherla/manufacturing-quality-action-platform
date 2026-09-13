from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    unit_id: str = Field(min_length=1, max_length=100)
    station_id: str = Field(min_length=1, max_length=100)
    equipment_id: str = Field(min_length=1, max_length=100)
    test_name: str = Field(min_length=1, max_length=100)
    value: float
    unit: str = Field(min_length=1, max_length=30)
    timestamp: datetime
    source: str = Field(default="equipment_simulator", max_length=100)

    @field_validator("timestamp")
    @classmethod
    def timezone_required(cls, value: datetime):
        if value.tzinfo is None:
            raise ValueError("timestamp must include a timezone")
        return value


class RuleIn(BaseModel):
    test_name: str
    station_id: str
    lower_limit: float
    upper_limit: float
    failure_action: str = "HOLD_AND_RETEST"
    version: str = "v1"

    @field_validator("upper_limit")
    @classmethod
    def upper_must_be_valid(cls, value: float, info):
        lower = info.data.get("lower_limit")
        if lower is not None and value <= lower:
            raise ValueError("upper_limit must be greater than lower_limit")
        return value


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

