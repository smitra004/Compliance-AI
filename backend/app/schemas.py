from pydantic import BaseModel, EmailStr
from typing import Optional
from typing import Literal


# -------------------------
# Authentication
# -------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    identifier: str  # username or email


# -------------------------
# User Creation
# -------------------------

class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: Literal[
        "central_admin",
        "admin",
        "manager",
        "auditor",
        "viewer",
    ]
    department: str | None = None

# -------------------------
# User Response
# -------------------------

class UserResponse(BaseModel):

    id: int

    username: str

    email: str

    role: str

    department: str

    status: str

    created_by: Optional[str] = None

    created_at: Optional[str] = None

    updated_at: Optional[str] = None

    is_active: bool


# -------------------------
# Update User
# -------------------------

class UserUpdate(BaseModel):

    username: Optional[str] = None

    email: Optional[EmailStr] = None

    role: Optional[str] = None

    department: Optional[str] = None

    status: Optional[str] = None

    is_active: Optional[bool] = None


# -------------------------
# Password Reset
# -------------------------

class PasswordUpdate(BaseModel):
    password: str


# -------------------------
# Department
# -------------------------

class DepartmentCreate(BaseModel):
    name: str


class DepartmentResponse(BaseModel):
    name: str


# -------------------------
# User Profile
# -------------------------

class UserProfile(BaseModel):

    id: int

    username: str

    email: str

    role: str

    department: str

    status: str