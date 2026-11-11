from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database.connection import get_db
from app.database.models import Business, User
from app.schemas.appointment import AvailabilityRead
from app.services.booking import list_available_slots

router = APIRouter(prefix="/availability", tags=["availability"])
public_router = APIRouter(prefix="/public/{slug}/availability", tags=["public"])


@router.get("", response_model=AvailabilityRead)
def owner_availability(
    service_id: int,
    day: date = Query(..., alias="date"),
    staff_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AvailabilityRead:
    slots = list_available_slots(db, current_user.business_id, service_id, day, staff_id)
    return AvailabilityRead(date=day, service_id=service_id, slots=slots)


@public_router.get("", response_model=AvailabilityRead)
def public_availability(
    slug: str,
    service_id: int,
    day: date = Query(..., alias="date"),
    staff_id: int | None = None,
    db: Session = Depends(get_db),
) -> AvailabilityRead:
    business = db.scalar(select(Business).where(Business.slug == slug))
    if not business:
        raise HTTPException(status_code=404, detail="Salon not found.")
    slots = list_available_slots(db, business.id, service_id, day, staff_id)
    return AvailabilityRead(date=day, service_id=service_id, slots=slots)
