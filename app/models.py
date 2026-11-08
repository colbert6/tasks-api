from datetime import date, datetime
from enum import StrEnum

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, field_validator


class Status(StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    done = "done"


class Priority(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"


def _no_numbers(v):
    if isinstance(v, (int, float)):
        raise ValueError("expected ISO date string")
    return v


Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Description = Annotated[str, Field(max_length=10_000)]
DueDate = Annotated[date, BeforeValidator(_no_numbers)]


class TaskBase(BaseModel):
    title: Title
    description: Description | None = None
    status: Status = Status.pending
    priority: Priority = Priority.medium
    due_date: DueDate | None = None


class TaskCreate(TaskBase):
    model_config = ConfigDict(extra="forbid")


class TaskUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Title | None = None
    description: Description | None = None
    status: Status | None = None
    priority: Priority | None = None
    due_date: DueDate | None = None

    @field_validator("title", "status", "priority")
    @classmethod
    def not_null(cls, v):
        # Defaults aren't validated, so this only fires on an explicit null.
        if v is None:
            raise ValueError("may not be null")
        return v


class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime


class TaskPage(BaseModel):
    items: list[Task]
    total: int
    limit: int
    offset: int
