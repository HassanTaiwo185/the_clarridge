import random
import json
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

OTP_TTL_SECONDS = 180  # 3 minutes


def generate_otp(email: str) -> str:
    return str(random.randint(100000, 999999))


from common.email import send_transactional_email


def send_otp_email(email, otp):
    """
    Sends OTP verification email using Brevo API.
    """
    html_content = f"""
    <div style="font-family: -apple-system, Arial, sans-serif; max-width: 500px; margin: 0 auto;">
      <div style="background-color: #0a1f44; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: #ffffff; margin: 0; font-weight: normal;">Verify Your Email</h2>
      </div>
      <div style="background-color: #f8f9fb; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
        <p>Your verification code is:</p>
        <h1 style="color: #0a1f44; letter-spacing: 4px;">{otp}</h1>
        <p style="color: #6c757d; font-size: 13px;">This code expires in 3 minutes.</p>
      </div>
    </div>
    """
    send_transactional_email(email, "Your Verification Code", html_content)


def send_approval_email(email):
    html_content = """
    <div style="font-family: -apple-system, Arial, sans-serif; max-width: 500px; margin: 0 auto;">
      <div style="background-color: #0a1f44; padding: 20px; border-radius: 8px 8px 0 0;">
        <h2 style="color: #ffffff; margin: 0; font-weight: normal;">Account Approved</h2>
      </div>
      <div style="background-color: #f8f9fb; padding: 24px; border-radius: 0 0 8px 8px; border: 1px solid #e5e7eb; border-top: none;">
        <p>Your account has been approved. You can now log in.</p>
      </div>
    </div>
    """
    send_transactional_email(email, "Your Account Has Been Approved", html_content)

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

