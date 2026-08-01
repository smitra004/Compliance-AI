import sqlite3
from datetime import datetime, timedelta

from app.security import hash_password

from app import config

DB = config.DB_PATH


def connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_users():

    conn = connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        username TEXT UNIQUE NOT NULL,

        email TEXT UNIQUE NOT NULL,

        password TEXT NOT NULL,

        role TEXT NOT NULL,

        department TEXT NOT NULL DEFAULT 'General',

        status TEXT NOT NULL DEFAULT 'Active',

        created_by TEXT DEFAULT 'System',

        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,

        is_active INTEGER DEFAULT 1

    )
    """)

    # ---------- Database Migration ----------
    columns = [c["name"] for c in conn.execute("PRAGMA table_info(users)")]

    if "department" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN department TEXT DEFAULT 'General'"
        )

    if "status" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'Active'"
        )

    if "created_by" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN created_by TEXT DEFAULT 'System'"
        )

    if "created_at" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN created_at TEXT"
        )
        conn.execute(
            "UPDATE users SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
        )

    if "updated_at" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN updated_at TEXT"
        )
        conn.execute(
            "UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE updated_at IS NULL"
        )

    # ---------- Authentication Upgrade ----------

    if "google_id" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN google_id TEXT"
        )

    if "email_verified" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN email_verified INTEGER DEFAULT 0"
        )

    if "password_changed" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN password_changed INTEGER DEFAULT 0"
        )

    if "otp" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN otp TEXT"
        )

    if "otp_expiry" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN otp_expiry TEXT"
        )

    if "refresh_token" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN refresh_token TEXT"
        )

    if "refresh_token_expiry" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN refresh_token_expiry TEXT"
        )

    if "failed_attempts" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0"
        )

    if "locked_until" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN locked_until TEXT"
        )

    if "last_login" not in columns:
        conn.execute(
            "ALTER TABLE users ADD COLUMN last_login TEXT"
        )

    conn.commit()

    admin = conn.execute(
        "SELECT * FROM users WHERE username='admin'"
    ).fetchone()

    if admin is None:

        conn.execute(
            """
            INSERT INTO users
            (
                username,
                email,
                password,
                role,
                department,
                status,
                created_by,
                email_verified,
                password_changed
            )
            VALUES(?,?,?,?,?,?,?,?,?)

            """,
            ("admin",
             "teamcomplianceai@gmail.com",
             hash_password("Admin@123"),
             "central_admin",
             "Global",
             "Active",
             "System",
             1,
             1  # password_changed
            ),
        )

    conn.commit()
    conn.close()


def get_user(username):

    conn = connection()

    user = conn.execute(
        "SELECT * FROM users WHERE username=?",
        (username,)
    ).fetchone()

    conn.close()

    return user


def get_user_by_username(username):

    """Full row for a single user, including the password hash —
    used by app.auth.authenticate_user() during login. Wraps
    get_user() and converts sqlite3.Row -> a plain dict, since
    sqlite3.Row doesn't support .get() and authenticate_user() relies
    on that."""

    row = get_user(username)

    return dict(row) if row else None


def get_user_by_identifier(identifier):

    """Look up a user by username OR email — used by the forgot-
    password flow, where the person may enter either."""

    conn = connection()

    row = conn.execute(
        "SELECT * FROM users WHERE username=? OR email=?",
        (identifier, identifier)
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def get_all_users():

    conn = connection()

    rows = conn.execute(
        """
        SELECT
            id,
            username,
            email,
            role,
            department,
            status,
            created_by,
            created_at,
            updated_at,
            is_active
        FROM users
        ORDER BY username
        """
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]

def update_department(user_id, department):

    conn = connection()

    conn.execute(
        """
        UPDATE users

        SET
            department=?,
            updated_at=CURRENT_TIMESTAMP

        WHERE id=?
        """,
        (
            department,
            user_id,
        ),
    )

    conn.commit()
    conn.close()


def create_user(
    username,
    email,
    password,
    role,
    department,
    status,
    created_by,
):

    conn = connection()

    conn.execute(
        """
        INSERT INTO users
        (
            username,
            email,
            password,
            role,
            department,
            status,
            created_by,
            email_verified,
            password_changed
        )
        VALUES(?,?,?,?,?,?,?,?,?)
        """,
        (
            username,
            email,
            hash_password(password),
            role,
            department,
            status,
            created_by,
            0,      # email not verified
            0       # force password change on first login
        ),
    )

    conn.commit()
    conn.close()

def update_role(user_id, role):

    conn = connection()

    conn.execute(
        """
        UPDATE users
        SET
            role=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (
            role,
            user_id,
        ),
    )

    conn.commit()
    conn.close()

    # -----------------------------
    # Synchronize ABAC permissions
    # -----------------------------
    from app.employee_db import (
        ensure_abac_profile,
        update_employee_access_profile,
        get_clearance_levels,
        get_regulations,
    )

    ensure_abac_profile(user_id)

    clearance_levels = {
        c["clearance_name"]: c["id"]
        for c in get_clearance_levels()
    }

    regulations = get_regulations()

    all_regulation_ids = [r["id"] for r in regulations]

    if role == "central_admin":

        update_employee_access_profile(
            user_id=user_id,
            clearance_level_id=clearance_levels["Top Secret"],
            allowed_regulation_ids=all_regulation_ids,
            permissions={
                "can_view_reports": True,
                "can_download": True,
                "can_export": True,
                "can_delete": True,
                "can_view_pii": True,
                "can_view_financial": True,
            },
        )

    elif role == "admin":

        update_employee_access_profile(
            user_id=user_id,
            clearance_level_id=clearance_levels["Restricted"],
            allowed_regulation_ids=all_regulation_ids,
            permissions={
                "can_view_reports": True,
                "can_download": True,
                "can_export": True,
                "can_delete": True,
                "can_view_pii": True,
                "can_view_financial": True,
            },
        )

    elif role == "manager":

        update_employee_access_profile(
            user_id=user_id,
            clearance_level_id=clearance_levels["Confidential"],
            allowed_regulation_ids=all_regulation_ids,
            permissions={
                "can_view_reports": True,
                "can_download": True,
                "can_export": True,
                "can_delete": False,
                "can_view_pii": True,
                "can_view_financial": True,
            },
        )

    elif role == "auditor":

        update_employee_access_profile(
            user_id=user_id,
            clearance_level_id=clearance_levels["Confidential"],
            allowed_regulation_ids=all_regulation_ids,
            permissions={
                "can_view_reports": True,
                "can_download": True,
                "can_export": True,
                "can_delete": False,
                "can_view_pii": False,
                "can_view_financial": False,
            },
        )

    else:

        update_employee_access_profile(
            user_id=user_id,
            clearance_level_id=clearance_levels["Internal"],
            allowed_regulation_ids=[],
            permissions={
                "can_view_reports": True,
                "can_download": False,
                "can_export": False,
                "can_delete": False,
                "can_view_pii": False,
                "can_view_financial": False,
            },
        )


def update_password(user_id, password):

    conn = connection()

    conn.execute(
        """
        UPDATE users

        SET
            password=?,
            password_changed=1,
            updated_at=CURRENT_TIMESTAMP

        WHERE id=?
        """,
        (
            hash_password(password),
            user_id,
        ),
    )

    conn.commit()
    conn.close()

def get_users_by_department(department):

    conn = connection()

    rows = conn.execute(
        """
        SELECT
            id,
            username,
            email,
            role,
            department,
            status,
            is_active
        FROM users

        WHERE department=?

        ORDER BY username
        """,
        (department,),
    ).fetchall()

    conn.close()

    return [dict(r) for r in rows]


def get_departments():

    conn = connection()

    rows = conn.execute(
        """
        SELECT DISTINCT department

        FROM users

        ORDER BY department
        """
    ).fetchall()

    conn.close()

    return [r["department"] for r in rows]


def delete_user(user_id):

    conn = connection()

    conn.execute(
        "DELETE FROM users WHERE id=?",
        (user_id,)
    )

    conn.commit()

    conn.close()

def get_user_by_email(email):

    conn = connection()

    row = conn.execute(
        "SELECT * FROM users WHERE email=?",
        (email,)
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def save_otp(email, otp, expiry):

    conn = connection()

    conn.execute(
        """
        UPDATE users
        SET otp=?,
            otp_expiry=?
        WHERE email=?
        """,
        (otp, expiry, email)
    )

    conn.commit()
    conn.close()


def verify_email(email):

    conn = connection()

    conn.execute(
        """
        UPDATE users
        SET email_verified=1
        WHERE email=?
        """,
        (email,)
    )

    conn.commit()
    conn.close()


def clear_otp(email):

    conn = connection()

    conn.execute(
        """
        UPDATE users
        SET otp=NULL,
            otp_expiry=NULL
        WHERE email=?
        """,
        (email,)
    )

    conn.commit()
    conn.close()


def save_refresh_token(email, token, expiry):

    conn = connection()

    conn.execute(
        """
        UPDATE users
        SET refresh_token=?,
            refresh_token_expiry=?
        WHERE email=?
        """,
        (token, expiry, email)
    )

    conn.commit()
    conn.close()

def update_last_login(user_id):

    conn = connection()

    conn.execute(
        """
        UPDATE users
        SET last_login=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

def increment_failed_attempts(user_id):

    conn = connection()

    conn.execute(
        """
        UPDATE users

        SET failed_attempts = failed_attempts + 1

        WHERE id=?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

def reset_failed_attempts(user_id):

    conn = connection()

    conn.execute(
        """
        UPDATE users

        SET failed_attempts=0,
            locked_until=NULL

        WHERE id=?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

def lock_account(user_id, minutes=15):

    until = (
        datetime.utcnow() +
        timedelta(minutes=minutes)
    ).isoformat()

    conn = connection()

    conn.execute(
        """
        UPDATE users

        SET locked_until=?

        WHERE id=?
        """,
        (until, user_id),
    )

    conn.commit()
    conn.close()

def get_user_by_refresh_token(token):

    conn = connection()

    row = conn.execute(
        """
        SELECT *

        FROM users

        WHERE refresh_token=?
        """,
        (token,),
    ).fetchone()

    conn.close()

    return dict(row) if row else None

def clear_refresh_token(email):

    conn = connection()

    conn.execute(
        """
        UPDATE users

        SET
            refresh_token=NULL,
            refresh_token_expiry=NULL

        WHERE email=?
        """,
        (email,),
    )

    conn.commit()
    conn.close()

def update_google_id(email, google_id):

    conn = connection()

    conn.execute(
        """
        UPDATE users

        SET google_id=?,
            email_verified=1

        WHERE email=?
        """,
        (
            google_id,
            email,
        ),
    )

    conn.commit()
    conn.close()