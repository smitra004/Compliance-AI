from datetime import datetime, timedelta

from fastapi import HTTPException

from app.email_utils import (
    send_password_reset_email,
    send_password_changed_email,
)
from app.security import (
    generate_otp,
    validate_password,
    verify_password,
)
from app.user_db import (
    clear_otp,
    get_user_by_identifier,
    save_otp,
    update_password,
)


OTP_EXPIRY_MINUTES = 10


# ---------------------------------------------------------
# Forgot Password
# ---------------------------------------------------------

def forgot_password(identifier: str):

    user = get_user_by_identifier(identifier)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    otp = generate_otp()

    expiry = (
        datetime.utcnow()
        + timedelta(minutes=OTP_EXPIRY_MINUTES)
    ).isoformat()

    save_otp(
        user["email"],
        otp,
        expiry,
    )

    sent = send_password_reset_email(
        user["email"],
        otp,
    )

    if not sent:
        raise HTTPException(
            status_code=500,
            detail="Unable to send reset email.",
        )

    return {
        "message": "Password reset OTP sent."
    }


# ---------------------------------------------------------
# Verify Reset OTP
# ---------------------------------------------------------

def verify_reset_otp(
    identifier: str,
    otp: str,
):

    user = get_user_by_identifier(identifier)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if user["otp"] != otp:
        raise HTTPException(
            status_code=400,
            detail="Invalid OTP.",
        )

    if user["otp_expiry"] is None:
        raise HTTPException(
            status_code=400,
            detail="OTP expired.",
        )

    expiry = datetime.fromisoformat(
        user["otp_expiry"]
    )

    if datetime.utcnow() > expiry:

        clear_otp(user["email"])

        raise HTTPException(
            status_code=400,
            detail="OTP expired.",
        )

    return {
        "message": "OTP verified."
    }


# ---------------------------------------------------------
# Reset Password
# ---------------------------------------------------------

def reset_password(
    identifier: str,
    otp: str,
    new_password: str,
):

    verify_reset_otp(
        identifier,
        otp,
    )

    ok, msg = validate_password(
        new_password
    )

    if not ok:
        raise HTTPException(
            status_code=400,
            detail=msg,
        )

    user = get_user_by_identifier(
        identifier
    )

    update_password(
        user["id"],
        new_password,
    )

    clear_otp(
        user["email"]
    )

    send_password_changed_email(
        user["email"]
    )

    return {
        "message":
        "Password reset successful."
    }


# ---------------------------------------------------------
# First Login Password Change
# ---------------------------------------------------------

def change_first_password(
    username: str,
    old_password: str,
    new_password: str,
):

    user = get_user_by_identifier(
        username
    )

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not verify_password(
        old_password,
        user["password"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Current password incorrect.",
        )

    ok, msg = validate_password(
        new_password
    )

    if not ok:
        raise HTTPException(
            status_code=400,
            detail=msg,
        )

    update_password(
        user["id"],
        new_password,
    )

    send_password_changed_email(
        user["email"]
    )

    return {
        "message":
        "Password updated successfully."
    }