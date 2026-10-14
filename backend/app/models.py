from datetime import date
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator


class DraftTask(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    importance: Literal["normal", "high"] = "normal"
    first_step: str | None = Field(default=None, min_length=1, max_length=500)
    first_step_origin: Literal["explicit", "suggested", "user"] | None = None
    due_date: date | None = None
    due_at: AwareDatetime | None = None

    @model_validator(mode="after")
    def validate_fields(self):
        if self.due_date is not None and self.due_at is not None:
            raise ValueError("Use either due_date or due_at.")
        if (self.first_step is None) != (self.first_step_origin is None):
            raise ValueError("First step and its origin must be set together.")
        return self


class ConfirmedTask(DraftTask):
    id: UUID
    start_friction: Literal["low", "medium", "high"] | None = None
    status: Literal["todo", "done"] = "todo"
    created_at: AwareDatetime


class RankRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tasks: list[ConfirmedTask]
    timezone: str

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone.")
        return value

    @model_validator(mode="after")
    def unique_ids(self):
        if len({task.id for task in self.tasks}) != len(self.tasks):
            raise ValueError("Task IDs must be unique.")
        return self


class RankedTask(BaseModel):
    id: UUID
    reasons: list[str]


class ExtractRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brain_dump: str = Field(min_length=1, max_length=10000)
    timezone: str

    @field_validator("brain_dump")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Enter a brain dump containing some text.")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Use a valid IANA timezone.")
        return value
