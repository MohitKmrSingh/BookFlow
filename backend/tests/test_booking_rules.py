from datetime import time

from app.database.models import Appointment, WorkingHours
from app.services.booking import add_minutes, is_slot_free, times_overlap


def test_add_minutes_crosses_hour():
    assert add_minutes(time(9, 45), 30) == time(10, 15)


def test_intervals_overlap_only_when_intersecting():
    assert times_overlap(time(9), time(10), time(9, 30), time(10, 30))
    assert not times_overlap(time(9), time(10), time(10), time(11))


def test_slot_must_fit_inside_working_hours():
    hours = WorkingHours(
        staff_id=1, weekday=0, start_time=time(9), end_time=time(17), is_closed=False
    )
    assert is_slot_free(time(9), time(10), hours, [])
    assert not is_slot_free(time(8, 30), time(9, 30), hours, [])
    assert not is_slot_free(time(16, 30), time(17, 30), hours, [])


def test_existing_booking_blocks_overlapping_slot():
    hours = WorkingHours(
        staff_id=1, weekday=0, start_time=time(9), end_time=time(17), is_closed=False
    )
    booking = Appointment(
        id=10, staff_id=1, appointment_date=None, start_time=time(10), end_time=time(11),
        business_id=1, customer_id=1, service_id=1, status="confirmed",
    )
    assert not is_slot_free(time(10, 30), time(11, 30), hours, [booking])
    assert is_slot_free(time(11), time(12), hours, [booking])


def test_closed_day_has_no_slots():
    hours = WorkingHours(
        staff_id=1, weekday=6, start_time=time(9), end_time=time(17), is_closed=True
    )
    assert not is_slot_free(time(9), time(10), hours, [])
