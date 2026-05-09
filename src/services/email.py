"""SMTP email service.

This is an *infrastructure* service: a thin wrapper around an external
system (SMTP) that any app can use without depending on a specific
business domain.

When SMTP is not configured, ``send_email`` logs the message instead
of sending it (handy for local dev). For production, swap this out for
an async/queued implementation or a transactional-email provider
client (AWS SES, Postmark, Resend, ...).
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from src.core.config import settings

logger = logging.getLogger(__name__)


def send_email(*, to: str, subject: str, body: str) -> None:
    if not settings.emails_enabled:
        logger.info("[email mock] To: %s | Subject: %s\n%s", to, subject, body)
        return

    message = EmailMessage()
    message["From"] = (
        f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>"
        if settings.EMAILS_FROM_NAME
        else str(settings.EMAILS_FROM_EMAIL)
    )
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
            if settings.SMTP_TLS:
                smtp.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            smtp.send_message(message)
        logger.info("Sent email to %s (%s)", to, subject)
    except Exception:  # noqa: BLE001 — never crash the request because email failed
        logger.exception("Failed to send email to %s", to)
