from datetime import date, time

from pydantic import BaseModel, EmailStr, Field


class CustomerIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=8, max_length=32)
    email: EmailStr | None = None


class AppointmentCreate(BaseModel):
    service_id: int
    staff_id: int | None = Field(
        default=None,
        description="Omit or set null to book with any available staff.",
    )
    appointment_date: date
    start_time: time
    customer: CustomerIn
    notes: str | None = None


class AppointmentReschedule(BaseModel):
    staff_id: int | None = None
    appointment_date: date
    start_time: time


class AppointmentStatusUpdate(BaseModel):
    status: str = Field(pattern="^(pending|confirmed|cancelled|completed|no_show)$")


class AppointmentRead(BaseModel):
    id: int
    business_id: int
    customer_id: int
    service_id: int
    staff_id: int
    appointment_date: date
    start_time: time
    end_time: time
    status: str
    notes: str | None
    customer_name: str | None = None
    service_name: str | None = None
    staff_name: str | None = None

    model_config = {"from_attributes": True}


class SlotRead(BaseModel):
    start_time: time
    end_time: time
    staff_id: int
    staff_name: str


class AvailabilityRead(BaseModel):
    date: date
    service_id: int
    slots: list[SlotRead]
