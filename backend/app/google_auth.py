from datetime import datetime, timedelta

from fastapi import HTTPException
from google.auth.transport import requests
from google.oauth2 import id_token

from app import config
from app.security import (
    create_access_token,
    create_refresh_token,
)
from app.user_db import (
    get_user_by_email,
    save_refresh_token,
    update_google_id,
)


def google_login(id_token_str: str):

    try:

        info = id_token.verify_oauth2_token(
            id_token_str,
            requests.Request(),
            config.GOOGLE_CLIENT_ID,
        )

    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid Google token",
        )

    email = info["email"]

    google_id = info["sub"]

    verified = info.get(
        "email_verified",
        False,
    )

    if not verified:

        raise HTTPException(
            status_code=403,
            detail="Google email not verified",
        )

    user = get_user_by_email(email)

    if user is None:

        raise HTTPException(
            status_code=403,
            detail="This email is not registered by your administrator.",
        )

    if user.get("google_id") is None:

        update_google_id(
            email,
            google_id,
        )

        user = get_user_by_email(email)

    access = create_access_token(user)

    refresh = create_refresh_token(user)

    expiry = (
        datetime.utcnow() +
        timedelta(days=30)
    ).isoformat()

    save_refresh_token(
        email,
        refresh,
        expiry,
    )

    return {

        "access_token": access,

        "refresh_token": refresh,

        "token_type": "bearer",

        "user": {

            "id": user["id"],

            "username": user["username"],

            "email": user["email"],

            "role": user["role"],

            "department": user["department"],

            "status": user["status"],

            "email_verified": True,

            "password_changed": bool(
                user["password_changed"]
            ),
        },
    }