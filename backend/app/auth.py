from datetime import datetime, timedelta

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from app import abac, config
from app.schemas import LoginRequest


pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)

# HTTPBearer with auto_error=False so a missing/malformed Authorization
# header falls through to our own 401 below instead of FastAPI's default
# (less informative) 403.
_bearer_scheme = HTTPBearer(auto_error=False)


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
    # Deferred import: rbac.py imports require_bearer from this module, so
    # importing rbac at module load time here would create an auth<->rbac
    # circular import. By call time both modules are fully loaded.
    from app.rbac import get_user_permissions

    payload = {

        # Standard JWT Subject
        "sub": user["username"],

        # User Information
        "id": user["id"],
        "username": user["username"],

        # RBAC
        "role": user["role"],

        # Permissions resolved from ROLE_PERMISSIONS (mirrors
        # permissions.js) at issue time, so the frontend can render off
        # `permissions` without re-deriving them from `role`.
        "permissions": get_user_permissions(user),

        # Department Isolation
        "department": user["department"],

        # Account Status
        "status": user.get("status", "Active"),

        # Expiration
        "exp": datetime.utcnow() + timedelta(hours=8),
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


# ---------------------------------------------------------
# Login
# ---------------------------------------------------------

def authenticate_user(req: LoginRequest) -> dict:
    """Verify username/password and issue a JWT.

    Assumes app.user_db exposes `get_user_by_username(username)` returning
    a dict with at least id/username/password(hash)/role/department/status,
    or None if no such user exists — the same CRUD surface user_db.py
    already exposes for get_all_users/create_user/etc.
    """
    from app.user_db import get_user_by_username

    user = get_user_by_username(req.username)

    if not user or not verify_password(req.password, user["password"]):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    if user.get("status", "Active") != "Active":
        raise HTTPException(
            status_code=403,
            detail="Account is inactive",
        )

    from app.employee_db import ensure_abac_profile
    ensure_abac_profile(user["id"])

    token = create_access_token(user)

    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": user["password_changed"] == 0,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "department": user["department"],
            "status": user.get("status", "Active"),
        },
    }


# ---------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------

def require_bearer(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> dict:
    """Base auth dependency. Decodes the bearer token and returns the
    full claims dict (id, username, role, department, status, exp).
    Every other auth dependency in this app builds on this one."""
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    try:
        claims = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    return claims


def require_roles(*roles: str):
    """Usage: claims: dict = Depends(require_roles("central_admin", "admin"))"""

    def dependency(claims: dict = Depends(require_bearer)) -> dict:
        if claims.get("role") not in roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient role",
            )
        return claims

    return dependency


def require_department(*departments: str):
    """Usage: claims: dict = Depends(require_department("Finance", "Legal"))

    central_admin bypasses department scoping entirely, matching the
    department-isolation behavior used throughout main.py/rbac.py.
    """

    def dependency(claims: dict = Depends(require_bearer)) -> dict:
        if claims.get("role") == "central_admin":
            return claims
        if claims.get("department") not in departments:
            raise HTTPException(
                status_code=403,
                detail="Department access denied",
            )
        return claims

    return dependency


def attrs_from_claims(claims: dict) -> dict:
    """Build the ABAC attribute set (department/region/clearance_level/
    business_unit) for a request. The JWT only ever carries `department`,
    so this delegates to abac.normalize_attributes to fill in the rest
    from DEFAULT_ATTRIBUTES."""
    return abac.normalize_attributes(claims)
