import logging
import smtplib
from datetime import datetime, timezone
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.models import Appointment, Notification

logger = logging.getLogger("bookflow.notifications")


def log_notification(
    db: Session,
    appointment: Appointment,
    message_type: str,
    payload: str,
) -> Notification:
    """Persist a notification attempt; send email when SMTP and customer email are configured."""
    settings = get_settings()
    recipient = appointment.customer.email if appointment.customer else None
    channel = "email" if settings.smtp_host and recipient else "log"
    record = Notification(
        appointment_id=appointment.id,
        message_type=message_type,
        channel=channel,
        status="pending",
        payload=payload,
    )
    db.add(record)
    db.flush()

    if channel == "log":
        record.status = "sent"
        record.sent_at = datetime.now(timezone.utc)
        logger.info("%s | appointment=%s | %s", message_type, appointment.id, payload)
        return record

    try:
        message = EmailMessage()
        message["Subject"] = f"Booking update — {appointment.business.name if appointment.business else 'BookFlow'}"
        message["From"] = settings.smtp_from
        message["To"] = recipient
        message.set_content(
            f"Hello {appointment.customer.name},\n\n{payload}\n\n"
            f"Business: {appointment.business.name if appointment.business else 'BookFlow'}\n"
            "Thank you."
        )
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(message)
        record.status = "sent"
        record.sent_at = datetime.now(timezone.utc)
        logger.info("Email %s sent for appointment=%s", message_type, appointment.id)
    except Exception:
        record.status = "failed"
        logger.exception("Email delivery failed for appointment=%s", appointment.id)
    return record


def notify_booking_confirmed(db: Session, appointment: Appointment) -> None:
    log_notification(
        db, appointment, "booking_confirmed",
        (f"Appointment #{appointment.id} confirmed for "
         f"{appointment.appointment_date} {appointment.start_time.strftime('%H:%M')}-"
         f"{appointment.end_time.strftime('%H:%M')}."),
    )


def notify_booking_cancelled(db: Session, appointment: Appointment) -> None:
    log_notification(db, appointment, "booking_cancelled", f"Appointment #{appointment.id} was cancelled.")


def notify_booking_rescheduled(db: Session, appointment: Appointment) -> None:
    log_notification(
        db, appointment, "booking_rescheduled",
        (f"Appointment #{appointment.id} moved to "
         f"{appointment.appointment_date} {appointment.start_time.strftime('%H:%M')}."),
    )
