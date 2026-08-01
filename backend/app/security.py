from datetime import datetime, timedelta
import secrets
import string

from jose import jwt
from passlib.context import CryptContext

from app import config


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ---------------------------------------------------------
# Password Hashing
# ---------------------------------------------------------

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


# ---------------------------------------------------------
# JWT Creation
# ---------------------------------------------------------

def create_access_token(user: dict):

    payload = {
        "sub": user["username"],
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "department": user["department"],
        "status": user.get("status", "Active"),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }

    return jwt.encode(
        payload,
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )

def create_refresh_token(user: dict):

    payload = {
        "sub": user["username"],
        "type": "refresh",
        "exp": datetime.utcnow() + timedelta(days=30),
    }

    return jwt.encode(
        payload,
        config.JWT_SECRET,
        algorithm=config.JWT_ALGORITHM,
    )

# ---------------------------------------------------------
# JWT Decode
# ---------------------------------------------------------

def decode_token(token: str):

    payload = jwt.decode(
        token,
        config.JWT_SECRET,
        algorithms=[config.JWT_ALGORITHM],
    )

    return payload

def generate_otp():

    return "".join(
        secrets.choice(string.digits)
        for _ in range(6)
    )

def generate_temp_password(length=12):

    alphabet = (
        string.ascii_letters
        + string.digits
        + "@#$%!"
    )

    return "".join(
        secrets.choice(alphabet)
        for _ in range(length)
    )

def validate_password(password):

    if len(password) < 8:
        return False, "Password must contain at least 8 characters."

    if not any(c.isupper() for c in password):
        return False, "Password needs one uppercase letter."

    if not any(c.islower() for c in password):
        return False, "Password needs one lowercase letter."

    if not any(c.isdigit() for c in password):
        return False, "Password needs one digit."

    if not any(c in "@#$%!*&" for c in password):
        return False, "Password needs one special character."

    return True, ""

def token_expired(payload):

    exp = payload.get("exp")

    if exp is None:
        return True

    return datetime.utcnow().timestamp() > exp