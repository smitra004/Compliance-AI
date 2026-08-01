from datetime import datetime, timedelta

from fastapi import HTTPException

from app.email_utils import (
    send_welcome_email,
)
from app.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_temp_password,
    validate_password,
    verify_password,
)
from app.user_db import (
    create_user,
    get_user_by_email,
    get_user_by_username,
    get_user_by_refresh_token,
    save_refresh_token,
    update_password,
)


# ---------------------------------------------------------
# Login
# ---------------------------------------------------------

def login(username: str, password: str):

    user = get_user_by_username(username)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    if user["status"] != "Active":
        raise HTTPException(
            status_code=403,
            detail="Account is inactive",
        )

    if not verify_password(
        password,
        user["password"],
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    access_token = create_access_token(user)

    refresh_token = create_refresh_token(user)

    expiry = (
        datetime.utcnow()
        + timedelta(days=30)
    ).isoformat()

    save_refresh_token(
        user["email"],
        refresh_token,
        expiry,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
            "department": user["department"],
            "status": user["status"],
            "email_verified": bool(
                user.get("email_verified", 0)
            ),
            "password_changed": bool(
                user.get("password_changed", 0)
            ),
        },
    }


# ---------------------------------------------------------
# Admin Creates User
# ---------------------------------------------------------

def admin_create_user(
    username,
    email,
    role,
    department,
    created_by,
):

    if get_user_by_username(username):
        raise HTTPException(
            400,
            "Username already exists",
        )

    if get_user_by_email(email):
        raise HTTPException(
            400,
            "Email already exists",
        )

    temp_password = generate_temp_password()

    create_user(
        username=username,
        email=email,
        password=temp_password,
        role=role,
        department=department,
        status="Active",
        created_by=created_by,
    )

    send_welcome_email(
        email,
        username,
        temp_password,
    )

    return {
        "message": "User created successfully.",
        "username": username,
    }


# ---------------------------------------------------------
# Change Password
# ---------------------------------------------------------

def first_password_change(
    username,
    old_password,
    new_password,
):

    user = get_user_by_username(username)

    if user is None:
        raise HTTPException(
            404,
            "User not found",
        )

    if not verify_password(
        old_password,
        user["password"],
    ):
        raise HTTPException(
            401,
            "Old password incorrect",
        )

    ok, msg = validate_password(
        new_password,
    )

    if not ok:
        raise HTTPException(
            400,
            msg,
        )

    update_password(
        user["id"],
        new_password,
    )

    return {
        "message":
        "Password updated successfully."
    }


# ---------------------------------------------------------
# Refresh Token
# ---------------------------------------------------------

def refresh_login(refresh_token: str):

    try:
        payload = decode_token(refresh_token)

        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=401,
                detail="Invalid refresh token",
            )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
        )

    user = get_user_by_refresh_token(refresh_token)

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Refresh token expired.",
        )

    access = create_access_token(user)

    return {
        "access_token": access,
        "token_type": "bearer",
    }