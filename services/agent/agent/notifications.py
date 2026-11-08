"""Staff notification service supporting Email-to-SMS gateways, Resend API, and simulated deliveries."""

import asyncio
from email.message import EmailMessage
import os
import smtplib
import time
from typing import Any
import httpx

# In-memory store for incoming staff replies
INCOMING_REPLIES: list[dict[str, Any]] = []


def record_inbound_reply(sender: str, body: str, raw_email_id: str | None = None) -> dict[str, Any]:
    """Records an incoming text/email reply from an employee."""
    reply_record = {
        "reply_id": f"rep_{len(INCOMING_REPLIES) + 1}",
        "sender": sender,
        "body": body.strip(),
        "received_at": time.strftime("%I:%M %p"),
        "raw_email_id": raw_email_id,
    }
    INCOMING_REPLIES.append(reply_record)
    return reply_record


def get_staff_replies(filter_query: str | None = None) -> list[dict[str, Any]]:
    """Returns recent replies, optionally filtered by sender phone or keyword."""
    if not filter_query:
        return INCOMING_REPLIES
    q = filter_query.lower()
    return [r for r in INCOMING_REPLIES if q in r["sender"].lower() or q in r["body"].lower()]


def format_staff_sms_body(
    message: str,
    manager_name: str = "Taylor Morgan",
    restaurant_phone: str = "(619) 555-0144",
    floor_phone: str = "(619) 555-0182",
) -> str:
    """Formats professional restaurant SMS with manager signature and direct callback info."""
    clean_msg = message.strip()
    return (
        f"{clean_msg}\n\n"
        f"— {manager_name}\n"
        f"Reply directly to this text, call the floor at {floor_phone}, or message back to {manager_name.split()[0]} at {restaurant_phone}."
    )
CARRIER_GATEWAYS: dict[str, str] = {
    "verizon": "vtext.com",
    "att": "txt.att.net",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "cricket": "mms.cricketwireless.net",
    "uscellular": "email.uscc.net",
    "boost": "myboostmobile.com",
}


def format_sms_gateway_address(phone_number: str, carrier: str) -> str:
    """Sanitizes 10-digit US phone number and appends carrier SMS gateway."""
    digits = "".join(filter(str.isdigit, phone_number))
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise ValueError(f"Phone number must be a 10-digit US number, got: {phone_number}")

    domain = CARRIER_GATEWAYS.get(carrier.lower().strip())
    if not domain:
        supported = ", ".join(CARRIER_GATEWAYS.keys())
        raise ValueError(f"Unsupported carrier '{carrier}'. Supported carriers: {supported}")

    return f"{digits}@{domain}"


async def send_via_resend(to_email: str, subject: str, message: str) -> dict[str, Any]:
    """Sends SMS notification via Resend REST API (Email-to-SMS gateway)."""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        raise ValueError("RESEND_API_KEY environment variable is not configured.")

    from_email = os.getenv("RESEND_FROM_EMAIL", "Remi Staff Alerts <onboarding@resend.dev>")

    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "text": message,
            },
        )
        res.raise_for_status()
        return res.json()


def _send_smtp_sync(to_email: str, subject: str, message: str) -> None:
    """Synchronous SMTP sender run in background thread."""
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    from_email = os.getenv("SMTP_FROM_EMAIL", user)

    msg = EmailMessage()
    msg.set_content(message)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(msg)


async def send_via_smtp(to_email: str, subject: str, message: str) -> dict[str, Any]:
    """Sends SMS notification via standard SMTP."""
    user = os.getenv("SMTP_USER")
    if not user:
        raise ValueError("SMTP_USER environment variable is not configured.")
    await asyncio.to_thread(_send_smtp_sync, to_email, subject, message)
    return {"status": "sent", "channel": "smtp", "recipient": to_email}


async def send_staff_sms(
    phone_number: str,
    carrier: str,
    message: str,
    manager_name: str | None = None,
    restaurant_phone: str | None = None,
    floor_phone: str | None = None,
    subject: str = "Remi Restaurant Alert",
) -> dict[str, Any]:
    """Dispatches staff SMS using Resend API, SMTP, or mock simulation if unconfigured."""
    # Allow overriding destination with a fixed test recipient in .env
    # Useful for Resend free tier sandbox (which restricts delivery to verified account)
    test_target_override = os.getenv("RESEND_TEST_RECIPIENT_OVERRIDE")
    if test_target_override:
        target_address = test_target_override.strip()
    else:
        target_address = format_sms_gateway_address(phone_number, carrier)

    # Format message with professional manager signature and callback phone numbers
    mgr = manager_name or os.getenv("DEFAULT_MANAGER_SIGNATURE", "Taylor Morgan")
    phone = restaurant_phone or os.getenv("RESTAURANT_CONTACT_PHONE", "(619) 555-0144")
    floor = floor_phone or os.getenv("FLOOR_CONTACT_PHONE", "(619) 555-0182")
    formatted_message = format_staff_sms_body(
        message, manager_name=mgr, restaurant_phone=phone, floor_phone=floor
    )

    # 1. Prefer Resend if API key is provided
    if os.getenv("RESEND_API_KEY"):
        res = await send_via_resend(target_address, subject, formatted_message)
        return {
            "status": "success",
            "provider": "resend",
            "gateway_address": target_address,
            "resend_id": res.get("id"),
            "formatted_message": formatted_message,
        }

    # 2. Try SMTP if configured
    if os.getenv("SMTP_USER"):
        await send_via_smtp(target_address, subject, formatted_message)
        return {
            "status": "success",
            "provider": "smtp",
            "gateway_address": target_address,
            "formatted_message": formatted_message,
        }

    # 3. Fallback to local mock simulator for development & demos
    mock_base_url = os.getenv("MOCK_POS_BASE_URL", "http://localhost:8001").rstrip("/")
    async with httpx.AsyncClient(base_url=mock_base_url, timeout=3.0) as client:
        try:
            res = await client.post(
                "/notifications/sms",
                json={
                    "phone_number": phone_number,
                    "carrier": carrier,
                    "gateway_address": target_address,
                    "message": formatted_message,
                },
            )
            return res.json()
        except Exception:
            return {
                "status": "simulated",
                "provider": "mock",
                "gateway_address": target_address,
                "formatted_message": formatted_message,
                "note": "Neither RESEND_API_KEY nor SMTP_USER configured; message simulated locally.",
            }
