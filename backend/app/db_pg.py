"""Optional PostgreSQL mirror of the audit trail.

SQLite (`db.py`) remains the source of truth for the single-instance demo —
it's zero-config and ships with the repo. When `DATABASE_URL` is set (see
`docker-compose.yml` / `k8s/postgres.yaml`), every audit event and saved scan
is additionally mirrored into Postgres via SQLAlchemy, which is what a
multi-replica Kubernetes deployment should read/write from instead of a local
SQLite file. Mirroring is best-effort: a Postgres outage never breaks the
request path.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app import config

_engine = None
_SessionLocal = None
_available = False

if config.POSTGRES_CONFIGURED:
    try:
        from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
        from sqlalchemy.orm import declarative_base, sessionmaker

        Base = declarative_base()

        class AuditLogPG(Base):
            __tablename__ = "audit_log"
            id = Column(Integer, primary_key=True, autoincrement=True)
            timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
            user = Column(String(255))
            role = Column(String(64))
            department = Column(String(128))
            action = Column(String(128))
            target = Column(String(512))
            detail = Column(Text)

        class ScanRecordPG(Base):
            __tablename__ = "scan_records"
            scan_id = Column(String(64), primary_key=True)
            tenant_id = Column(String(128))
            document_name = Column(String(512))
            compliance_score = Column(Integer)
            total_violations = Column(Integer)
            raw_json = Column(Text)
            created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

        _engine = create_engine(config.DATABASE_URL, pool_pre_ping=True)
        Base.metadata.create_all(_engine)
        _SessionLocal = sessionmaker(bind=_engine)
        _available = True
        print("[db_pg] PostgreSQL mirror enabled")
    except Exception as e:  # noqa: BLE001
        print(f"[db_pg] PostgreSQL unavailable ({e}); continuing on SQLite only")
        _available = False


def is_available() -> bool:
    return _available


def mirror_audit(
        user: str,
        role: str,
        department: str,
        action: str,
        target: str,
        detail: str,
    ) -> None:
    if not _available:
        return
    try:
        with _SessionLocal() as session:
            session.add(
                AuditLogPG(
                    user=user,
                    role=role,
                    department=department,
                    action=action,
                    target=target,
                    detail=detail,
                )
            )
            session.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[db_pg] mirror_audit failed (non-fatal): {e}")


def mirror_scan(scan_id: str, tenant_id: str, document_name: str,
                 compliance_score: int, total_violations: int, raw_json: str) -> None:
    if not _available:
        return
    try:
        with _SessionLocal() as session:
            session.merge(ScanRecordPG(
                scan_id=scan_id, tenant_id=tenant_id, document_name=document_name,
                compliance_score=compliance_score, total_violations=total_violations,
                raw_json=raw_json,
            ))
            session.commit()
    except Exception as e:  # noqa: BLE001
        print(f"[db_pg] mirror_scan failed (non-fatal): {e}")
