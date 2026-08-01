from datetime import datetime, timedelta

from fastapi import HTTPException

from app.email_utils import send_otp_email
from app.security import generate_otp
from app.user_db import (
    clear_otp,
    get_user_by_email,
    save_otp,
    verify_email,
)


OTP_EXPIRY_MINUTES = 10


# ---------------------------------------------------------
# Send Verification OTP
# ---------------------------------------------------------

def send_verification_otp(email: str):

    user = get_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if user.get("email_verified"):
        return {
            "message": "Email is already verified."
        }

    otp = generate_otp()

    expiry = (
        datetime.utcnow() +
        timedelta(minutes=OTP_EXPIRY_MINUTES)
    ).isoformat()

    save_otp(
        email=email,
        otp=otp,
        expiry=expiry,
    )

    sent = send_otp_email(
        email=email,
        otp=otp,
    )

    if not sent:
        raise HTTPException(
            status_code=500,
            detail="Unable to send OTP email.",
        )

    return {
        "message": "OTP sent successfully.",
    }


# ---------------------------------------------------------
# Verify OTP
# ---------------------------------------------------------

def verify_email_otp(email: str, otp: str):

    user = get_user_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    stored_otp = user.get("otp")
    expiry = user.get("otp_expiry")

    if stored_otp is None:
        raise HTTPException(
            status_code=400,
            detail="No OTP has been generated.",
        )

    if stored_otp != otp:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP.",
        )

    if expiry is None:
        raise HTTPException(
            status_code=400,
            detail="OTP expired.",
        )

    if datetime.utcnow() > datetime.fromisoformat(expiry):
        clear_otp(email)

        raise HTTPException(
            status_code=400,
            detail="OTP has expired.",
        )

    verify_email(email)

    clear_otp(email)

    return {
        "message": "Email verified successfully.",
    }


# ---------------------------------------------------------
# Resend OTP
# ---------------------------------------------------------

def resend_otp(email: str):

    return send_verification_otp(email)