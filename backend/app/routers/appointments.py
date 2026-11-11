from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import get_current_user, require_owner
from app.database.connection import get_db
from app.database.models import Appointment, Business, User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentRead,
    AppointmentReschedule,
    AppointmentStatusUpdate,
)
from app.services.booking import cancel_appointment, create_appointment, reschedule_appointment, to_appointment_read

router = APIRouter(prefix="/appointments", tags=["appointments"])
public_router = APIRouter(prefix="/public/{slug}/appointments", tags=["public"])


def _loaded(query):
    return query.options(
        joinedload(Appointment.customer),
        joinedload(Appointment.service),
        joinedload(Appointment.staff),
    )


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    day: date | None = Query(default=None, alias="date"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AppointmentRead]:
    query = _loaded(select(Appointment).where(Appointment.business_id == current_user.business_id))
    if day:
        query = query.where(Appointment.appointment_date == day)
    query = query.order_by(Appointment.appointment_date, Appointment.start_time)
    return [to_appointment_read(row) for row in db.scalars(query).unique()]


@router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def owner_create_appointment(
    payload: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    appointment = create_appointment(db, current_user.business_id, payload)
    return to_appointment_read(appointment)


@router.post("/{appointment_id}/cancel", response_model=AppointmentRead)
def owner_cancel(
    appointment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    appointment = db.scalar(
        _loaded(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.business_id == current_user.business_id,
            )
        )
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    return to_appointment_read(cancel_appointment(db, appointment))


@router.post("/{appointment_id}/reschedule", response_model=AppointmentRead)
def owner_reschedule(
    appointment_id: int,
    payload: AppointmentReschedule,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    appointment = db.scalar(
        _loaded(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.business_id == current_user.business_id,
            )
        )
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    updated = reschedule_appointment(
        db,
        appointment,
        payload.appointment_date,
        payload.start_time,
        payload.staff_id,
    )
    return to_appointment_read(updated)


@router.patch("/{appointment_id}/status", response_model=AppointmentRead)
def update_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    current_user: User = Depends(require_owner),
    db: Session = Depends(get_db),
) -> AppointmentRead:
    appointment = db.scalar(
        _loaded(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.business_id == current_user.business_id,
            )
        )
    )
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found.")
    if payload.status == "cancelled":
        return to_appointment_read(cancel_appointment(db, appointment))
    appointment.status = payload.status
    db.commit()
    db.refresh(appointment)
    return to_appointment_read(appointment)


@public_router.post("", response_model=AppointmentRead, status_code=status.HTTP_201_CREATED)
def public_create_appointment(
    slug: str,
    payload: AppointmentCreate,
    db: Session = Depends(get_db),
) -> AppointmentRead:
    business = db.scalar(select(Business).where(Business.slug == slug))
    if not business:
        raise HTTPException(status_code=404, detail="Salon not found.")
    appointment = create_appointment(db, business.id, payload)
    return to_appointment_read(appointment)
