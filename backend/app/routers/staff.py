from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_owner
from app.database.connection import get_db
from app.database.models import Business, Staff, User, WorkingHours
from app.schemas.staff import StaffCreate, StaffRead, StaffUpdate, WorkingHoursIn, WorkingHoursRead

router = APIRouter(prefix="/staff", tags=["staff"])
public_router = APIRouter(prefix="/public/{slug}/staff", tags=["public"])


def _staff_query(business_id: int):
    return select(Staff).options(joinedload(Staff.working_hours)).where(Staff.business_id == business_id)


@router.get("", response_model=list[StaffRead])
def list_staff(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Staff]:
    return list(db.scalars(_staff_query(current_user.business_id).order_by(Staff.name)).unique())


@router.post("", response_model=StaffRead, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreate,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> Staff:
    staff = Staff(
        business_id=current_user.business_id,
        name=payload.name,
        phone=payload.phone,
        email=payload.email,
    )
    db.add(staff)
    db.flush()
    for hours in payload.working_hours:
        db.add(WorkingHours(staff_id=staff.id, **hours.model_dump()))
    db.commit()
    return db.scalar(_staff_query(current_user.business_id).where(Staff.id == staff.id))


@router.patch("/{staff_id}", response_model=StaffRead)
def update_staff(
    staff_id: int,
    payload: StaffUpdate,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> Staff:
    staff = db.scalar(select(Staff).where(Staff.id == staff_id, Staff.business_id == current_user.business_id))
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)
    db.commit()
    return db.scalar(_staff_query(current_user.business_id).where(Staff.id == staff_id))


@router.put("/{staff_id}/working-hours", response_model=list[WorkingHoursRead])
def replace_working_hours(
    staff_id: int,
    hours: list[WorkingHoursIn],
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> list[WorkingHours]:
    staff = db.scalar(select(Staff).where(Staff.id == staff_id, Staff.business_id == current_user.business_id))
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    weekdays = [item.weekday for item in hours]
    if len(weekdays) != len(set(weekdays)):
        raise HTTPException(status_code=422, detail="Only one working-hours entry is allowed per weekday.")
    for existing in db.scalars(select(WorkingHours).where(WorkingHours.staff_id == staff_id)):
        db.delete(existing)
    db.flush()
    created: list[WorkingHours] = []
    for item in hours:
        row = WorkingHours(staff_id=staff_id, **item.model_dump())
        db.add(row)
        created.append(row)
    db.commit()
    return created


@public_router.get("", response_model=list[StaffRead])
def public_list_staff(slug: str, db: Session = Depends(get_db)) -> list[Staff]:
    business = db.scalar(select(Business).where(Business.slug == slug))
    if not business:
        raise HTTPException(status_code=404, detail="Salon not found.")
    return list(
        db.scalars(_staff_query(business.id).where(Staff.is_active.is_(True)).order_by(Staff.name)).unique()
    )
