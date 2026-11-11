from datetime import time

from pydantic import BaseModel, EmailStr, Field, model_validator


class WorkingHoursIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    is_closed: bool = False

    @model_validator(mode="after")
    def validate_time_range(self):
        if not self.is_closed and self.start_time >= self.end_time:
            raise ValueError("Working-hours end_time must be later than start_time.")
        return self


class WorkingHoursRead(WorkingHoursIn):
    id: int
    staff_id: int

    model_config = {"from_attributes": True}


class StaffCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = None
    email: EmailStr | None = None
    working_hours: list[WorkingHoursIn] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_weekdays(self):
        weekdays = [item.weekday for item in self.working_hours]
        if len(weekdays) != len(set(weekdays)):
            raise ValueError("Only one working-hours entry is allowed per weekday.")
        return self


class StaffUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = None
    email: EmailStr | None = None
    is_active: bool | None = None


class StaffRead(BaseModel):
    id: int
    business_id: int
    name: str
    phone: str | None
    email: str | None
    is_active: bool
    working_hours: list[WorkingHoursRead] = Field(default_factory=list)

    model_config = {"from_attributes": True}
