"""SQLite persistence: immutable audit log + scan records."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from app import config
from app.models import AuditEntry, ScanRecord


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                detail TEXT NOT NULL
            )""")
        c.execute("""CREATE TABLE IF NOT EXISTS scans (
            scan_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS compliance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL,
            policy_updates REAL NOT NULL,
            training_completion REAL NOT NULL,
            audit_findings REAL NOT NULL,
            security_violations REAL NOT NULL,
            documentation_quality REAL NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS custom_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            policy_name TEXT NOT NULL,
            rules TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL DEFAULT '',
            tenant_id TEXT NOT NULL DEFAULT 'acmecorp')""")
            
        # Migration: check if version and updated_at exist in custom_policies
        cursor = c.execute("PRAGMA table_info(custom_policies)")
        cols = [col["name"] for col in cursor.fetchall()]
        if "version" not in cols:
            c.execute("ALTER TABLE custom_policies ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
        if "updated_at" not in cols:
            c.execute("ALTER TABLE custom_policies ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")
        if "tenant_id" not in cols:
            c.execute("ALTER TABLE custom_policies ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'acmecorp'")

        cursor = c.execute("PRAGMA table_info(audit)")
        cols = [col["name"] for col in cursor.fetchall()]

        if "department" not in cols:
            c.execute(
                "ALTER TABLE audit ADD COLUMN department TEXT NOT NULL DEFAULT 'Unknown'"
            )

        c.execute("""CREATE TABLE IF NOT EXISTS abac_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            resource TEXT NOT NULL,
            action TEXT NOT NULL,
            policies_evaluated TEXT NOT NULL,
            matched_policy TEXT NOT NULL,
            decision TEXT NOT NULL,
            reason TEXT NOT NULL,
            failed_conditions TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            environment_attributes TEXT NOT NULL,
            execution_time_ms REAL NOT NULL,
            ip_address TEXT DEFAULT '',
            device TEXT DEFAULT '',
            location TEXT DEFAULT '',
            session_id TEXT DEFAULT '',
            obligations TEXT DEFAULT ''
        )""")



def save_compliance_metric(date: str, policy_updates: float, training_completion: float, audit_findings: float, security_violations: float, documentation_quality: float):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO compliance_metrics (date, policy_updates, training_completion, audit_findings, security_violations, documentation_quality) "
            "VALUES (?,?,?,?,?,?)",
            (date, policy_updates, training_completion, audit_findings, security_violations, documentation_quality)
        )


def get_compliance_history():
    with _conn() as c:
        rows = c.execute("SELECT * FROM compliance_metrics ORDER BY date ASC").fetchall()
    return [dict(r) for r in rows]


def log_audit(
    actor: str,
    role: str,
    department: str,
    action: str,
    target: str,
    detail: str = "",
):
    with _conn() as c:
        c.execute(
            "INSERT INTO audit (timestamp, actor, role, department, action, target, detail) "
            "VALUES (?,?,?,?,?,?,?)",
            (datetime.now(timezone.utc).isoformat(), actor, role, department, action,
             target, detail),
        )


def get_audit(limit: int = 100) -> List[AuditEntry]:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [AuditEntry(
            id=r["id"],
            timestamp=datetime.fromisoformat(r["timestamp"]),
            actor=r["actor"],
            role=r["role"],
            department=r["department"],
            action=r["action"],
            target=r["target"],
            detail=r["detail"],
        ) for r in rows]


def save_scan(record: ScanRecord):
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO scans (scan_id, created_at, payload) "
            "VALUES (?,?,?)",
            (record.scan_id, record.created_at.isoformat(),
             record.model_dump_json()),
        )


def _normalize_scan_payload(payload: dict) -> dict:
    """Shared defaults/normalization applied to every stored scan payload
    before ScanRecord(**payload) — used by both get_scan() and list_scans()
    so the two code paths can never drift out of sync again."""
    payload.setdefault("department", "General")
    payload.setdefault("uploaded_by", "System")
    payload.setdefault("tenant_id", "acmecorp")

    # Older rows predate compliance_status/risk_level: derive them from the
    # persisted score using the same centralized bands, rather than leaving
    # them defaulted to "Non-Compliant"/"High" regardless of actual score.
    if "compliance_status" not in payload or "risk_level" not in payload:
        from app.pipeline.scoring import compliance_status_and_risk
        sr = compliance_status_and_risk(payload.get("compliance_score", 0))
        payload.setdefault("compliance_status", sr["status"])
        payload.setdefault("risk_level", sr["risk_level"])

    # Older scan rows persisted score_breakdown as a dict
    # ({"factor": points, ...}) before the model was changed to
    # List[Dict[str, Any]]. Without this, ScanRecord(**payload) raises a
    # pydantic validation error for any such row.
    sb = payload.get("score_breakdown", [])
    if isinstance(sb, dict):
        payload["score_breakdown"] = [
            {"factor": k, "detail": "", "points": v} for k, v in sb.items()
        ]
    elif sb is None:
        payload["score_breakdown"] = []

    return payload


def get_scan(scan_id: str) -> ScanRecord | None:
    with _conn() as c:
        row = c.execute("SELECT payload FROM scans WHERE scan_id=?",
                        (scan_id,)).fetchone()
    if not row:
        return None

    payload = _normalize_scan_payload(json.loads(row["payload"]))
    return ScanRecord(**payload)


def list_scans(tenant_id: str = None, limit: int = 50) -> List[ScanRecord]:
    with _conn() as c:
        if tenant_id:
            rows = c.execute(
                "SELECT scan_id, payload FROM scans ORDER BY created_at DESC"
            ).fetchall()

            scans = []
            for r in rows:
                try:
                    payload = _normalize_scan_payload(json.loads(r["payload"]))
                    s = ScanRecord(**payload)
                except Exception as e:
                    # One malformed/legacy row should never take down the
                    # whole dashboard/scans/trend list — skip it and log
                    # which scan_id and why, so it's still fixable/visible.
                    print(f"[db.list_scans] Skipping unparsable scan {r['scan_id']}: {e}")
                    continue

                if s.tenant_id == tenant_id:
                    scans.append(s)
                    if len(scans) >= limit:
                        break

            return scans

        rows = c.execute(
            "SELECT scan_id, payload FROM scans ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        records = []
        for r in rows:
            try:
                payload = _normalize_scan_payload(json.loads(r["payload"]))
                records.append(ScanRecord(**payload))
            except Exception as e:
                print(f"[db.list_scans] Skipping unparsable scan {r['scan_id']}: {e}")
                continue

        return records


def save_custom_policy(policy_name: str, rules: list[str], tenant_id: str = "acmecorp") -> int:
    with _conn() as c:
        row = c.execute(
            "SELECT MAX(version) as max_v FROM custom_policies WHERE policy_name=? AND tenant_id=?",
            (policy_name, tenant_id)
        ).fetchone()
        next_version = (row["max_v"] or 0) + 1 if row else 1
        
        cursor = c.execute(
            "INSERT INTO custom_policies (policy_name, rules, version, updated_at, tenant_id) VALUES (?,?,?,?,?)",
            (policy_name, json.dumps(rules), next_version, datetime.now(timezone.utc).isoformat(), tenant_id),
        )
        return cursor.lastrowid


def list_custom_policies(tenant_id: str = None) -> list[dict]:
    with _conn() as c:
        if tenant_id:
            rows = c.execute(
                "SELECT * FROM custom_policies WHERE tenant_id=? ORDER BY policy_name ASC, version DESC",
                (tenant_id,)
            ).fetchall()
        else:
            rows = c.execute("SELECT * FROM custom_policies ORDER BY policy_name ASC, version DESC").fetchall()
    return [
        {
            "id": r["id"],
            "policy_name": r["policy_name"],
            "rules": json.loads(r["rules"]),
            "version": r["version"],
            "updated_at": r["updated_at"],
            "tenant_id": r["tenant_id"]
        }
        for r in rows
    ]



def delete_custom_policy(policy_id: int):
    with _conn() as c:
        c.execute("DELETE FROM custom_policies WHERE id=?", (policy_id,))

def log_abac_audit(
    user: str,
    role: str,
    department: str,
    resource: str,
    action: str,
    policies_evaluated: list,
    matched_policy: str,
    decision: str,
    reason: str,
    failed_conditions: list,
    risk_score: int,
    environment_attributes: dict,
    execution_time_ms: float,
    ip_address: str = "",
    device: str = "",
    location: str = "",
    session_id: str = "",
    obligations: list = None,
):
    with _conn() as c:
        c.execute(
            """INSERT INTO abac_audit (
                timestamp, user, role, department, resource, action,
                policies_evaluated, matched_policy, decision, reason,
                failed_conditions, risk_score, environment_attributes,
                execution_time_ms, ip_address, device, location, session_id, obligations
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                user,
                role,
                department,
                resource,
                action,
                json.dumps(policies_evaluated or []),
                matched_policy or "NONE",
                decision,
                reason,
                json.dumps(failed_conditions or []),
                risk_score,
                json.dumps(environment_attributes or {}),
                execution_time_ms,
                ip_address,
                device,
                location,
                session_id,
                json.dumps(obligations or []),
            ),
        )


def get_abac_audit_logs(
    limit: int = 100,
    user: Optional[str] = None,
    department: Optional[str] = None,
    decision: Optional[str] = None,
    matched_policy: Optional[str] = None,
    min_risk: Optional[int] = None,
    search: Optional[str] = None,
) -> List[dict]:
    with _conn() as c:
        query = "SELECT * FROM abac_audit WHERE 1=1"
        params = []

        if user and user.strip():
            query += " AND user LIKE ?"
            params.append(f"%{user.strip()}%")

        if department and department.strip() and department.lower() != "all":
            query += " AND department = ?"
            params.append(department.strip())

        if decision and decision.strip() and decision.lower() != "all":
            query += " AND decision = ?"
            params.append(decision.strip().upper())

        if matched_policy and matched_policy.strip() and matched_policy.lower() != "all":
            query += " AND matched_policy = ?"
            params.append(matched_policy.strip())

        if min_risk is not None and min_risk > 0:
            query += " AND risk_score >= ?"
            params.append(min_risk)

        if search and search.strip():
            query += " AND (user LIKE ? OR action LIKE ? OR matched_policy LIKE ? OR resource LIKE ?)"
            s = f"%{search.strip()}%"
            params.extend([s, s, s, s])

        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = c.execute(query, params).fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["policies_evaluated"] = json.loads(d["policies_evaluated"]) if d.get("policies_evaluated") else []
        d["failed_conditions"] = json.loads(d["failed_conditions"]) if d.get("failed_conditions") else []
        d["environment_attributes"] = json.loads(d["environment_attributes"]) if d.get("environment_attributes") else {}
        d["obligations"] = json.loads(d["obligations"]) if d.get("obligations") else []
        if d.get("subject_attributes"):
            try:
                d["subject_attributes"] = json.loads(d["subject_attributes"])
            except Exception:
                pass
        if d.get("resource_attributes"):
            try:
                d["resource_attributes"] = json.loads(d["resource_attributes"])
            except Exception:
                pass
        if d.get("risk_breakdown"):
            try:
                d["risk_breakdown"] = json.loads(d["risk_breakdown"])
            except Exception:
                pass
        result.append(d)
    return result


def get_abac_dashboard_stats() -> dict:
    """Computes live enterprise governance KPIs dynamically from audit logs."""
    logs = get_abac_audit_logs(limit=500)
    total_requests = len(logs)

    if total_requests == 0:
        return {
            "total_requests": 0,
            "permit_count": 0,
            "deny_count": 0,
            "permit_rate": 100.0,
            "denial_rate": 0.0,
            "avg_risk_score": 5,
            "avg_evaluation_time_ms": 1.5,
            "most_triggered_policy": "GLOB-001",
            "most_applied_obligation": "Mask PAN",
            "high_risk_requests_today": 0,
        }

    permits = sum(1 for l in logs if l.get("decision") == "PERMIT")
    denies = sum(1 for l in logs if l.get("decision") == "DENY")
    permit_rate = round((permits / total_requests) * 100.0, 1)
    denial_rate = round((denies / total_requests) * 100.0, 1)

    avg_risk = round(sum(l.get("risk_score", 0) for l in logs) / total_requests, 1)
    avg_duration = round(sum(l.get("execution_time_ms", 1.2) for l in logs) / total_requests, 2)

    # Most triggered policy
    policy_counts: dict = {}
    obligation_counts: dict = {}
    high_risk_count = 0

    for l in logs:
        pol = l.get("matched_policy", "NONE")
        if pol and pol != "NONE":
            policy_counts[pol] = policy_counts.get(pol, 0) + 1

        obs = l.get("obligations") or []
        for ob in obs:
            obligation_counts[ob] = obligation_counts.get(ob, 0) + 1

        if l.get("risk_score", 0) >= 60:
            high_risk_count += 1

    most_policy = max(policy_counts.items(), key=lambda x: x[1])[0] if policy_counts else "GLOB-001"
    most_ob = max(obligation_counts.items(), key=lambda x: x[1])[0] if obligation_counts else "Mask PAN"

    return {
        "total_requests": total_requests,
        "permit_count": permits,
        "deny_count": denies,
        "permit_rate": permit_rate,
        "denial_rate": denial_rate,
        "avg_risk_score": avg_risk,
        "avg_evaluation_time_ms": avg_duration,
        "most_triggered_policy": most_policy,
        "most_applied_obligation": most_ob,
        "high_risk_requests_today": high_risk_count,
    }



def save_abac_audit_log(entry_dict: dict):
    with _conn() as c:
        # Check table schema for additional forensic columns
        cursor = c.execute("PRAGMA table_info(abac_audit)")
        cols = [col["name"] for col in cursor.fetchall()]
        if "subject_attributes" not in cols:
            try:
                c.execute("ALTER TABLE abac_audit ADD COLUMN subject_attributes TEXT DEFAULT ''")
                c.execute("ALTER TABLE abac_audit ADD COLUMN resource_attributes TEXT DEFAULT ''")
                c.execute("ALTER TABLE abac_audit ADD COLUMN risk_breakdown TEXT DEFAULT ''")
                c.execute("ALTER TABLE abac_audit ADD COLUMN policy_version TEXT DEFAULT 'v1.0.0'")
                c.execute("ALTER TABLE abac_audit ADD COLUMN integrity_signature TEXT DEFAULT ''")
            except Exception:
                pass

        c.execute(
            """INSERT INTO abac_audit (
                timestamp, user, role, department, resource, action,
                policies_evaluated, matched_policy, decision, reason,
                failed_conditions, risk_score, environment_attributes,
                execution_time_ms, ip_address, device, location, session_id, obligations,
                subject_attributes, resource_attributes, risk_breakdown, policy_version, integrity_signature
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                entry_dict.get("timestamp"),
                entry_dict.get("user"),
                entry_dict.get("role"),
                entry_dict.get("department"),
                entry_dict.get("resource_id", "RES-001"),
                entry_dict.get("requested_action", "Read"),
                json.dumps(entry_dict.get("evaluated_policies", [])),
                entry_dict.get("matched_policy", "NONE"),
                entry_dict.get("decision", "DENY"),
                entry_dict.get("reason", ""),
                json.dumps(entry_dict.get("failed_conditions", [])),
                entry_dict.get("risk_score", 0),
                json.dumps(entry_dict.get("environment_attributes", {})),
                entry_dict.get("evaluation_time_ms", 0.0),
                entry_dict.get("ip_address", "127.0.0.1"),
                entry_dict.get("device", "Corporate Workstation"),
                entry_dict.get("country", "US"),
                entry_dict.get("session_id", ""),
                json.dumps(entry_dict.get("obligations_applied", [])),
                json.dumps(entry_dict.get("subject_attributes", {})),
                json.dumps(entry_dict.get("resource_attributes", {})),
                json.dumps(entry_dict.get("risk_breakdown", [])),
                entry_dict.get("policy_version", "v1.0.0"),
                entry_dict.get("integrity_signature", ""),
            ),
        )



