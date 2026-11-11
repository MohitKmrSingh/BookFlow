from datetime import date, datetime, timedelta, time
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Appointment, Business, Customer, Service, Staff, WorkingHours
from app.schemas.appointment import AppointmentCreate, AppointmentRead, SlotRead
from app.services.notifications import notify_booking_confirmed, notify_booking_cancelled, notify_booking_rescheduled

SLOT_STEP_MINUTES = 15
BOOKABLE_STATUSES = ("pending", "confirmed")


class SlotUnavailable(HTTPException):
    def __init__(self, detail: str = "That time slot is not available.") -> None:
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


def add_minutes(value: time, minutes: int) -> time:
    dt = datetime.combine(date.today(), value) + timedelta(minutes=minutes)
    return dt.time()


def times_overlap(start_a: time, end_a: time, start_b: time, end_b: time) -> bool:
    return start_a < end_b and start_b < end_a


def to_appointment_read(appointment: Appointment) -> AppointmentRead:
    return AppointmentRead(
        id=appointment.id,
        business_id=appointment.business_id,
        customer_id=appointment.customer_id,
        service_id=appointment.service_id,
        staff_id=appointment.staff_id,
        appointment_date=appointment.appointment_date,
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        status=appointment.status,
        notes=appointment.notes,
        customer_name=appointment.customer.name if appointment.customer else None,
        service_name=appointment.service.name if appointment.service else None,
        staff_name=appointment.staff.name if appointment.staff else None,
    )


def get_or_create_customer(db: Session, business_id: int, name: str, phone: str, email: str | None) -> Customer:
    customer = db.scalar(
        select(Customer).where(Customer.business_id == business_id, Customer.phone == phone)
    )
    if customer:
        customer.name = name
        if email:
            customer.email = email
        return customer
    customer = Customer(business_id=business_id, name=name, phone=phone, email=email)
    db.add(customer)
    db.flush()
    return customer


def _service_for_business(db: Session, business_id: int, service_id: int) -> Service:
    service = db.scalar(
        select(Service).where(
            Service.id == service_id,
            Service.business_id == business_id,
            Service.is_active.is_(True),
        )
    )
    if not service:
        raise HTTPException(status_code=404, detail="Service not found.")
    return service


def _staff_for_business(db: Session, business_id: int, staff_id: int | None) -> list[Staff]:
    query = select(Staff).where(Staff.business_id == business_id, Staff.is_active.is_(True)).order_by(Staff.id)
    if staff_id is not None:
        query = query.where(Staff.id == staff_id)
    staff = list(db.scalars(query).unique())
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found.")
    return staff


def _working_hours_for(db: Session, staff_id: int, weekday: int) -> WorkingHours | None:
    return db.scalar(
        select(WorkingHours).where(WorkingHours.staff_id == staff_id, WorkingHours.weekday == weekday)
    )


def _existing_bookings(db: Session, staff_id: int, day: date) -> list[Appointment]:
    return list(
        db.scalars(
            select(Appointment)
            .where(
                Appointment.staff_id == staff_id,
                Appointment.appointment_date == day,
                Appointment.status.in_(BOOKABLE_STATUSES),
            )
            .with_for_update()
        )
    )


def is_slot_free(
    start: time,
    end: time,
    hours: WorkingHours,
    existing: list[Appointment],
    ignore_appointment_id: int | None = None,
) -> bool:
    if hours.is_closed:
        return False
    if start < hours.start_time or end > hours.end_time:
        return False
    for booking in existing:
        if ignore_appointment_id is not None and booking.id == ignore_appointment_id:
            continue
        if times_overlap(start, end, booking.start_time, booking.end_time):
            return False
    return True


def list_available_slots(
    db: Session,
    business_id: int,
    service_id: int,
    day: date,
    staff_id: int | None = None,
) -> list[SlotRead]:
    service = _service_for_business(db, business_id, service_id)
    staff_members = _staff_for_business(db, business_id, staff_id)
    weekday = day.weekday()
    slots: list[SlotRead] = []
    business = db.get(Business, business_id)
    try:
        local_now = datetime.now(ZoneInfo(business.timezone if business else "UTC"))
    except Exception:
        local_now = datetime.now(ZoneInfo("UTC"))
    if day < local_now.date():
        return []

    for member in staff_members:
        hours = _working_hours_for(db, member.id, weekday)
        if not hours or hours.is_closed:
            continue
        existing = list(
            db.scalars(
                select(Appointment).where(
                    Appointment.staff_id == member.id,
                    Appointment.appointment_date == day,
                    Appointment.status.in_(BOOKABLE_STATUSES),
                )
            )
        )
        cursor = hours.start_time
        while True:
            end = add_minutes(cursor, service.duration_minutes)
            if end > hours.end_time:
                break
            is_in_future = day > local_now.date() or cursor > local_now.time().replace(tzinfo=None)
            if is_in_future and is_slot_free(cursor, end, hours, existing):
                slots.append(
                    SlotRead(
                        start_time=cursor,
                        end_time=end,
                        staff_id=member.id,
                        staff_name=member.name,
                    )
                )
            cursor = add_minutes(cursor, SLOT_STEP_MINUTES)
            if cursor >= hours.end_time:
                break
    return slots


def create_appointment(db: Session, business_id: int, payload: AppointmentCreate) -> Appointment:
    business = db.get(Business, business_id)
    timezone_name = business.timezone if business else "UTC"
    try:
        business_now = datetime.now(ZoneInfo(timezone_name))
    except Exception:
        business_now = datetime.now(ZoneInfo("UTC"))
    if payload.appointment_date < business_now.date() or (
        payload.appointment_date == business_now.date()
        and payload.start_time <= business_now.time().replace(tzinfo=None)
    ):
        raise HTTPException(status_code=422, detail="Appointments must be booked for a future time.")
    service = _service_for_business(db, business_id, payload.service_id)
    end_time = add_minutes(payload.start_time, service.duration_minutes)
    candidates = _staff_for_business(db, business_id, payload.staff_id)
    weekday = payload.appointment_date.weekday()

    chosen: Staff | None = None
    for candidate in candidates:
        # Lock the staff row so two concurrent requests cannot both see an empty slot
        # and insert overlapping appointments for the same staff member.
        member = db.scalar(
            select(Staff).where(Staff.id == candidate.id, Staff.business_id == business_id).with_for_update()
        )
        if member is None or not member.is_active:
            continue
        hours = _working_hours_for(db, member.id, weekday)
        if not hours:
            continue
        existing = _existing_bookings(db, member.id, payload.appointment_date)
        if is_slot_free(payload.start_time, end_time, hours, existing):
            chosen = member
            break

    if chosen is None:
        raise SlotUnavailable("No staff member is free at that time.")

    customer = get_or_create_customer(
        db,
        business_id,
        payload.customer.name,
        payload.customer.phone,
        payload.customer.email,
    )
    appointment = Appointment(
        business_id=business_id,
        customer_id=customer.id,
        service_id=service.id,
        staff_id=chosen.id,
        appointment_date=payload.appointment_date,
        start_time=payload.start_time,
        end_time=end_time,
        status="confirmed",
        notes=payload.notes,
    )
    db.add(appointment)
    db.flush()
    db.refresh(appointment, attribute_names=["customer", "service", "staff"])
    notify_booking_confirmed(db, appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def cancel_appointment(db: Session, appointment: Appointment) -> Appointment:
    if appointment.status == "cancelled":
        return appointment
    appointment.status = "cancelled"
    notify_booking_cancelled(db, appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def reschedule_appointment(
    db: Session,
    appointment: Appointment,
    new_date: date,
    new_start: time,
    staff_id: int | None,
) -> Appointment:
    business = db.get(Business, appointment.business_id)
    timezone_name = business.timezone if business else "UTC"
    try:
        business_now = datetime.now(ZoneInfo(timezone_name))
    except Exception:
        business_now = datetime.now(ZoneInfo("UTC"))
    if new_date < business_now.date() or (
        new_date == business_now.date() and new_start <= business_now.time().replace(tzinfo=None)
    ):
        raise SlotUnavailable("Appointments must be moved to a future time.")
    service = _service_for_business(db, appointment.business_id, appointment.service_id)
    end_time = add_minutes(new_start, service.duration_minutes)
    target_staff_id = staff_id or appointment.staff_id
    members = _staff_for_business(db, appointment.business_id, target_staff_id)
    member = db.scalar(
        select(Staff).where(
            Staff.id == members[0].id, Staff.business_id == appointment.business_id
        ).with_for_update()
    )
    if member is None or not member.is_active:
        raise SlotUnavailable("Staff member is not available.")
    hours = _working_hours_for(db, member.id, new_date.weekday())
    if not hours:
        raise SlotUnavailable("Staff is not working on that day.")
    existing = _existing_bookings(db, member.id, new_date)
    if not is_slot_free(new_start, end_time, hours, existing, ignore_appointment_id=appointment.id):
        raise SlotUnavailable()

    appointment.staff_id = member.id
    appointment.appointment_date = new_date
    appointment.start_time = new_start
    appointment.end_time = end_time
    appointment.status = "confirmed"
    notify_booking_rescheduled(db, appointment)
    db.commit()
    db.refresh(appointment)
    return appointment
