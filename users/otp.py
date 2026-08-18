import random
import json
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

OTP_TTL_SECONDS = 180  # 3 minutes


def generate_otp(email: str) -> str:
    return str(random.randint(100000, 999999))


def send_otp_email(email: str, otp: str) -> None:
    send_mail(
        subject="Your verification code",
        message=f"Your verification code is {otp}. It expires in 3 minutes.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )


# ---------------------------------------------------------
# Registration OTP (email verification before account creation)
# ---------------------------------------------------------

def stash_pending_registration(email: str, otp: str, data: dict) -> None:
    """Store OTP + registration payload together, TTL'd, nothing hits the DB yet."""
    cache.set(
        f"pending_registration:{email}",
        json.dumps({"otp": otp, "data": data}),
        timeout=OTP_TTL_SECONDS,
    )


def get_pending_registration(email: str) -> dict | None:
    raw = cache.get(f"pending_registration:{email}")
    return json.loads(raw) if raw else None


def clear_pending_registration(email: str) -> None:
    cache.delete(f"pending_registration:{email}")


# ---------------------------------------------------------
# Password reset OTP
# ---------------------------------------------------------

def stash_password_reset_otp(email: str, otp: str) -> None:
    cache.set(f"password_reset:{email}", otp, timeout=OTP_TTL_SECONDS)


def get_password_reset_otp(email: str) -> str | None:
    return cache.get(f"password_reset:{email}")


def clear_password_reset_otp(email: str) -> None:
    cache.delete(f"password_reset:{email}")

def send_approval_email(email: str) -> None:
    send_mail(
        subject="Your account has been approved",
        message="Good news — your account has been approved by an administrator. You can now log in.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )