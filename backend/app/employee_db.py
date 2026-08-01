"""
Enterprise Employee ABAC Database & ORM Layer
Provides SQLAlchemy models for Department, Regulation, ClearanceLevel, EmployeePermission,
and EmployeeRegulation, synced directly with the existing `users` table.
"""
from __future__ import annotations

import sqlite3
from typing import Dict, List, Any, Optional
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    ForeignKey,
    Table,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session
from app import config

# SQLAlchemy Database Engine
engine = create_engine(
    f"sqlite:///{config.DB_PATH}",
    connect_args={"check_same_thread": False},
    echo=False,
)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()


class UserStub(Base):
    """Reflects/registers users table in SQLAlchemy metadata."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True)
    email = Column(String, unique=True)
    role = Column(String)
    department = Column(String)
    status = Column(String)


# Many-to-Many Table for User <-> Regulations
user_regulations = Table(
    "employee_regulations",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("regulation_id", Integer, ForeignKey("regulations.id", ondelete="CASCADE"), primary_key=True),
)


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    department_name = Column(String, unique=True, nullable=False)


class Regulation(Base):
    __tablename__ = "regulations"

    id = Column(Integer, primary_key=True, index=True)
    regulation_name = Column(String, unique=True, nullable=False)


class ClearanceLevel(Base):
    __tablename__ = "clearance_levels"

    id = Column(Integer, primary_key=True, index=True)
    clearance_name = Column(String, unique=True, nullable=False)
    rank = Column(Integer, nullable=False)


class EmployeePermission(Base):
    __tablename__ = "employee_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    clearance_level_id = Column(Integer, ForeignKey("clearance_levels.id"), nullable=False)
    can_view_reports = Column(Boolean, default=True, nullable=False)
    can_download = Column(Boolean, default=False, nullable=False)
    can_export = Column(Boolean, default=False, nullable=False)
    can_delete = Column(Boolean, default=False, nullable=False)
    can_view_pii = Column(Boolean, default=False, nullable=False)
    can_view_financial = Column(Boolean, default=False, nullable=False)

    clearance_level = relationship("ClearanceLevel")


def init_abac_db():
    """Create all tables and seed default Department, Regulation, and ClearanceLevel entries."""
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        # 1. Clearance Levels
        default_clearances = [
            ("Public", 1),
            ("Internal", 2),
            ("Confidential", 3),
            ("Restricted", 4),
            ("Top Secret", 5),
        ]
        for name, rank in default_clearances:
            existing = session.query(ClearanceLevel).filter_by(clearance_name=name).first()
            if not existing:
                session.add(ClearanceLevel(clearance_name=name, rank=rank))

        # 2. Regulations
        default_regulations = [
            "GDPR",
            "SOX",
            "ISO 27001",
            "HIPAA",
            "Internal Security",
            "Internal HR",
        ]
        for name in default_regulations:
            existing = session.query(Regulation).filter_by(regulation_name=name).first()
            if not existing:
                session.add(Regulation(regulation_name=name))

        # 3. Departments
        default_departments = [
            "HR",
            "Finance",
            "Legal",
            "Security",
            "Operations",
            "Engineering",
            "General",
        ]
        for name in default_departments:
            existing = session.query(Department).filter_by(department_name=name).first()
            if not existing:
                session.add(Department(department_name=name))

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def ensure_abac_profile(user_id: int):
    """
    Ensures that a user has an ABAC profile in the database.
    If absent, provisions a default 'Least Privilege' profile:
      - Clearance: Internal (rank 2)
      - Allowed Regulations: Internal Security, Internal HR
      - Permissions: can_view_reports=True; all other toggles=False
    """
    init_abac_db()
    session = SessionLocal()
    try:
        # Check permissions profile
        perm = session.query(EmployeePermission).filter_by(user_id=user_id).first()
        if not perm:
            internal_clearance = session.query(ClearanceLevel).filter_by(clearance_name="Internal").first()
            clearance_id = internal_clearance.id if internal_clearance else 2

            # Provision Principle of Least Privilege
            # Get the user's role
            user = session.query(UserStub).filter_by(id=user_id).first()
            role = user.role if user else "viewer"

            # Assign permissions based on role
            if role == "central_admin":
                perm = EmployeePermission(
                    user_id=user_id,
                    clearance_level_id=5,      # Top Secret
                    can_view_reports=True,
                    can_download=True,
                    can_export=True,
                    can_delete=True,
                    can_view_pii=True,
                    can_view_financial=True,
                )

            elif role == "admin":
                perm = EmployeePermission(
                    user_id=user_id,
                    clearance_level_id=4,      # Restricted
                    can_view_reports=True,
                    can_download=True,
                    can_export=True,
                    can_delete=True,
                    can_view_pii=True,
                    can_view_financial=True,
                )

            elif role == "manager":
                perm = EmployeePermission(
                    user_id=user_id,
                    clearance_level_id=3,
                    can_view_reports=True,
                    can_download=True,
                    can_export=True,
                    can_delete=False,
                    can_view_pii=True,
                    can_view_financial=True,
                )

            elif role == "auditor":
                perm = EmployeePermission(
                    user_id=user_id,
                    clearance_level_id=3,
                    can_view_reports=True,
                    can_download=True,
                    can_export=True,
                    can_delete=False,
                    can_view_pii=False,
                    can_view_financial=False,
                )

            else:
                # Viewer / Employee (Least Privilege)
                perm = EmployeePermission(
                    user_id=user_id,
                    clearance_level_id=2,
                    can_view_reports=True,
                    can_download=False,
                    can_export=False,
                    can_delete=False,
                    can_view_pii=False,
                    can_view_financial=False,
                )

            session.add(perm)

            # Default regulations: Internal Security, Internal HR
            internal_regs = session.query(Regulation).filter(
                Regulation.regulation_name.in_(["Internal Security", "Internal HR"])
            ).all()
            for reg in internal_regs:
                session.execute(
                    user_regulations.insert().values(user_id=user_id, regulation_id=reg.id)
                )

            session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_all_employees_access_profiles() -> List[Dict[str, Any]]:
    """
    Fetches all real users from the `users` table joined with their ABAC attributes.
    Ensures each user has an ABAC profile created.
    """
    init_abac_db()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    users_rows = cursor.execute(
        "SELECT id, username, email, role, department, status FROM users WHERE is_active = 1"
    ).fetchall()
    conn.close()

    profiles = []
    for u in users_rows:
        u_id = u["id"]
        ensure_abac_profile(u_id)
        profile = get_employee_access_profile(u_id)
        if profile:
            profiles.append(profile)

    return profiles


def get_employee_access_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetches full ABAC profile for a specific user."""
    init_abac_db()
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    user_row = cursor.execute(
        "SELECT id, username, email, role, department, status FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()

    if not user_row:
        return None

    session = SessionLocal()
    try:
        perm = session.query(EmployeePermission).filter_by(user_id=user_id).first()
        if not perm:
            session.close()
            ensure_abac_profile(user_id)
            session = SessionLocal()
            perm = session.query(EmployeePermission).filter_by(user_id=user_id).first()

        if not perm:
            # Should be unreachable (ensure_abac_profile always provisions a
            # row), but if it ever happens, fail safe with a least-privilege
            # profile instead of raising AttributeError on perm.* below and
            # taking down the whole endpoint (e.g. /api/scans iterates this
            # once per scan record).
            print(f"[employee_db] No EmployeePermission row for user_id={user_id} even after ensure_abac_profile(); using least-privilege fallback")
            return {
                "id": user_row["id"],
                "user_id": user_row["id"],
                "employee_id": f"EMP-{1000 + user_row['id']}",
                "name": user_row["username"],
                "username": user_row["username"],
                "email": user_row["email"],
                "role": user_row["role"],
                "department": user_row["department"] or "General",
                "status": user_row["status"],
                "clearance_level_id": 2,
                "clearance_level": "Internal",
                "clearance_rank": 2,
                "allowed_regulation_ids": [],
                "allowed_regulations": [],
                "permissions": {
                    "can_view_reports": True,
                    "can_download": False,
                    "can_export": False,
                    "can_delete": False,
                    "can_view_pii": False,
                    "can_view_financial": False,
                },
            }

        clearance = session.query(ClearanceLevel).filter_by(id=perm.clearance_level_id).first()

        # Fetch allowed regulation IDs & names
        reg_rows = session.execute(
            user_regulations.select().where(user_regulations.c.user_id == user_id)
        ).fetchall()
        reg_ids = [r.regulation_id for r in reg_rows]
        regs = session.query(Regulation).filter(Regulation.id.in_(reg_ids)).all() if reg_ids else []

        return {
            "id": user_row["id"],
            "user_id": user_row["id"],
            "employee_id": f"EMP-{1000 + user_row['id']}",
            "name": user_row["username"],
            "username": user_row["username"],
            "email": user_row["email"],
            "role": user_row["role"],
            "department": user_row["department"] or "General",
            "status": user_row["status"],
            "clearance_level_id": perm.clearance_level_id,
            "clearance_level": clearance.clearance_name if clearance else "Internal",
            "clearance_rank": clearance.rank if clearance else 2,
            "allowed_regulation_ids": reg_ids,
            "allowed_regulations": [r.regulation_name for r in regs],
            "permissions": {
                "can_view_reports": bool(perm.can_view_reports),
                "can_download": bool(perm.can_download),
                "can_export": bool(perm.can_export),
                "can_delete": bool(perm.can_delete),
                "can_view_pii": bool(perm.can_view_pii),
                "can_view_financial": bool(perm.can_view_financial),
            },
        }
    finally:
        session.close()


def update_employee_access_profile(
    user_id: int,
    clearance_level_id: int,
    allowed_regulation_ids: List[int],
    permissions: Dict[str, bool],
) -> Dict[str, Any]:
    """Updates ABAC clearance level, allowed regulations, and permission toggles for a user."""
    ensure_abac_profile(user_id)
    session = SessionLocal()
    try:
        perm = session.query(EmployeePermission).filter_by(user_id=user_id).first()
        if perm:
            perm.clearance_level_id = clearance_level_id
            perm.can_view_reports = permissions.get("can_view_reports", True)
            perm.can_download = permissions.get("can_download", False)
            perm.can_export = permissions.get("can_export", False)
            perm.can_delete = permissions.get("can_delete", False)
            perm.can_view_pii = permissions.get("can_view_pii", False)
            perm.can_view_financial = permissions.get("can_view_financial", False)

        # Clear existing regulations
        session.execute(
            user_regulations.delete().where(user_regulations.c.user_id == user_id)
        )
        # Re-insert regulations
        for reg_id in set(allowed_regulation_ids):
            session.execute(
                user_regulations.insert().values(user_id=user_id, regulation_id=reg_id)
            )

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

    return get_employee_access_profile(user_id)


def get_clearance_levels() -> List[Dict[str, Any]]:
    init_abac_db()
    session = SessionLocal()
    try:
        levels = session.query(ClearanceLevel).order_by(ClearanceLevel.rank.asc()).all()
        return [{"id": l.id, "clearance_name": l.clearance_name, "rank": l.rank} for l in levels]
    finally:
        session.close()


def get_regulations() -> List[Dict[str, Any]]:
    init_abac_db()
    session = SessionLocal()
    try:
        regs = session.query(Regulation).order_by(Regulation.id.asc()).all()
        return [{"id": r.id, "regulation_name": r.regulation_name} for r in regs]
    finally:
        session.close()


def get_departments() -> List[Dict[str, Any]]:
    init_abac_db()
    session = SessionLocal()
    try:
        depts = session.query(Department).order_by(Department.id.asc()).all()
        return [{"id": d.id, "department_name": d.department_name} for d in depts]
    finally:
        session.close()
