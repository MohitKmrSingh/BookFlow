from decimal import Decimal

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    price: Decimal = Field(ge=0)
    duration_minutes: int = Field(gt=0, le=480)


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    duration_minutes: int | None = Field(default=None, gt=0, le=480)
    is_active: bool | None = None


class ServiceRead(BaseModel):
    id: int
    business_id: int
    name: str
    description: str | None
    price: Decimal
    duration_minutes: int
    is_active: bool

    model_config = {"from_attributes": True}
