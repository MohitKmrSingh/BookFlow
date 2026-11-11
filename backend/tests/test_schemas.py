import pytest
from pydantic import ValidationError

from app.schemas.staff import WorkingHoursIn


def test_working_hours_reject_non_increasing_time():
    with pytest.raises(ValidationError):
        WorkingHoursIn(weekday=0, start_time="18:00", end_time="09:00", is_closed=False)


def test_closed_day_can_have_equal_times():
    item = WorkingHoursIn(weekday=6, start_time="00:00", end_time="00:00", is_closed=True)
    assert item.is_closed is True



def test_staff_schema_rejects_duplicate_weekdays():
    from app.schemas.staff import StaffCreate

    with pytest.raises(ValidationError):
        StaffCreate(
            name="Taylor",
            working_hours=[
                {"weekday": 0, "start_time": "09:00", "end_time": "17:00"},
                {"weekday": 0, "start_time": "10:00", "end_time": "18:00"},
            ],
        )
