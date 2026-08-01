"""Policy Compliance Checker — FastAPI application."""
from __future__ import annotations

import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import secrets

from app.security import validate_password
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel as PydanticBaseModel

from app.password_service import (
    forgot_password as forgot_password_service,
    reset_password as password_reset_service,
    change_first_password,
)

from app.otp_service import (
    send_verification_otp,
    verify_email_otp,
)

from app.auth_service import (
    refresh_login,
)

from app.google_auth import (
    google_login,
)

class RemediateRequest(PydanticBaseModel):
    violation_ids: list[str]


class CustomPolicyRequest(PydanticBaseModel):
    policy_name: str
    rules: list[str]

class OTPRequest(PydanticBaseModel):
    email: str


class VerifyOTPRequest(PydanticBaseModel):
    email: str
    otp: str


class ResetPasswordRequest(PydanticBaseModel):
    identifier: str
    otp: str
    new_password: str


class ChangePasswordRequest(PydanticBaseModel):
    old_password: str
    new_password: str


class RefreshTokenRequest(PydanticBaseModel):
    refresh_token: str


class GoogleLoginRequest(PydanticBaseModel):
    credential: str

from app import abac, config, db, db_pg, cache, email_utils, metrics, notifications
from app.auth import (
    authenticate_user,
    require_bearer,
    require_roles,
    require_department,
    attrs_from_claims,
)
from app.azure_clients import PurviewClient
from app.models import DashboardStats, ScanRecord, Severity, ResolvedViolation
from app.pipeline.orchestrator import run_pipeline
from app.pipeline.crew import run_crew_analysis
from app.pipeline.vectorstore import get_store
from app.pipeline.scoring import calculate_compliance_score, compliance_status_and_risk
from app.rbac import (
    require,
    filter_documents,
    has_document_access,
)
from app.schemas import (
    UserCreate,
    UserUpdate,
    LoginRequest,
    ForgotPasswordRequest,
)
from app.seed import seed
from app.user_db import (
    get_all_users,
    get_user_by_identifier,
    get_users_by_department,
    get_departments,
    create_user,
    update_role,
    update_department,
    update_password,
    delete_user,
    init_users,
)

app = FastAPI(title="Policy Compliance Checker", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "https://compliance-ai-83en.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics.instrument(app)

from fastapi import Request
from fastapi.responses import JSONResponse

_error_log_path = Path(__file__).resolve().parent.parent / "error.log"

@app.exception_handler(Exception)
async def _log_unhandled_exceptions(request: Request, exc: Exception):
    tb = traceback.format_exc()
    entry = f"\n{'='*80}\n{datetime.now().isoformat()}  {request.method} {request.url}\n{tb}\n"
    print(entry)
    try:
        with open(_error_log_path, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass
    return JSONResponse(status_code=500, content={"detail": str(exc), "type": type(exc).__name__})


@app.on_event("startup")
async def _startup():

    db.init_db()

    init_users()

    get_store()

    #await seed()


def central_admin_only(
    claims: dict = Depends(require_bearer),
):
    if claims["role"] != "central_admin":
        raise HTTPException(
            status_code=403,
            detail="Central Admin access required",
        )

    return claims


def get_effective_department(claims: dict):
    if claims["role"] == "central_admin":
        return None

    return claims["department"]


@app.get("/api/auth/attribute-options")
def attribute_options():
    return {
        "departments": [
            "Finance",
            "HR",
            "Legal",
            "Security",
            "Operations",
            "Engineering"
        ],
        "regions": [
            "Global",
            "EU",
            "US",
            "APAC"
        ],
        "clearance_levels": [
            "public",
            "internal",
            "confidential",
            "restricted"
        ],
        "roles": [
            "central_admin",
            "admin",
            "manager",
            "auditor",
            "viewer"
        ]
    }


@app.get("/api/departments")
def departments(
    claims: dict = Depends(require_bearer),
):
    departments = get_departments()

    if not departments:
        departments = [
            "Finance",
            "HR",
            "Legal",
            "Security",
            "Operations",
            "Engineering"
        ]

    return departments


@app.get("/api/users")
def users(
    claims: dict = Depends(require_bearer),
):

    if claims["role"] not in [
        "central_admin",
        "admin",
    ]:
        raise HTTPException(
            status_code=403,
            detail="Permission denied"
        )

    if claims["role"] == "central_admin":
        return get_all_users()

    return get_users_by_department(
        claims["department"]
    )


@app.post("/api/users")
def add_user(
    req: UserCreate,
    claims: dict = Depends(require_bearer),
):
    if claims["role"] == "central_admin":

        if req.role == "central_admin":
            department = "Global"
        else:
            department = req.department

    elif claims["role"] == "admin":
        department = claims["department"]

        if req.role in ["admin", "central_admin"]:
            raise HTTPException(
                status_code=403,
                detail="Department admins cannot create admins."
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Not allowed"
        )

    ok, msg = validate_password(req.password)

    if not ok:
        raise HTTPException(
            status_code=400,
            detail=msg,
        )

    # Create the user here
    create_user(
            username=req.username,
            email=req.email,
            password=req.password,
            role=req.role,
            department=department,
            status="Active",
            created_by=claims["username"],
        )

    sent = email_utils.send_welcome_email(
        email=req.email,
        username=req.username,
        temporary_password=req.password,
    )

    print("Welcome email sent:", sent)

    return {
        "message": "User created successfully",
        "email_sent": sent,
    }


@app.put("/api/users/{user_id}/role")
def change_role(
    user_id: int,
    req: UserUpdate,
    claims: dict = Depends(central_admin_only),
):

    if req.role is None:
        raise HTTPException(
            status_code=400,
            detail="Role required"
        )

    update_role(
        user_id,
        req.role,
    )

    # Automatically assign Global department to Central Admins
    if req.role == "central_admin":
        update_department(
            user_id,
            "Global",
        )

    return {
        "message": "Role updated"
    }


@app.put("/api/users/{user_id}/department")
def change_department(
    user_id: int,
    req: UserUpdate,
    claims: dict = Depends(central_admin_only),
):

    if req.department is None:
        raise HTTPException(
            status_code=400,
            detail="Department required",
        )

    update_department(
        user_id,
        req.department,
    )

    return {
        "message": "Department updated"
    }

@app.delete("/api/users/{user_id}")
def remove_user(
    user_id: int,
    claims: dict = Depends(central_admin_only),
):

    if user_id == claims["id"]:
        raise HTTPException(
            status_code=400,
            detail="You cannot delete your own account"
        )

    delete_user(user_id)

    return {
        "message": "User deleted"
    }


@app.get("/api/users/me")
def current_user(
    claims: dict = Depends(require_bearer),
):

    return {
        "id": claims["id"],
        "username": claims["username"],
        "role": claims["role"],
        "department": claims["department"],
        "status": claims["status"],
        "permissions": claims.get("permissions", []),
    }


@app.post("/api/auth/token")
def login(req: LoginRequest):

    return authenticate_user(req)

@app.post("/api/auth/send-otp")
def send_otp(req: OTPRequest):

    return send_verification_otp(
        req.email
    )

@app.post("/api/auth/verify-otp")
def verify_otp(req: VerifyOTPRequest):

    return verify_email_otp(
        req.email,
        req.otp,
    )

@app.post("/api/auth/reset-password")
def reset_password_endpoint(req: ResetPasswordRequest):
    return password_reset_service(
        req.identifier,
        req.otp,
        req.new_password,
    )

@app.post("/api/auth/change-password")
def change_password_endpoint(
    req: ChangePasswordRequest,
    claims: dict = Depends(require_bearer),
):
    return change_first_password(
        claims["username"],
        req.old_password,
        req.new_password,
    )

@app.post("/api/auth/refresh")
def refresh_token_endpoint(
    req: RefreshTokenRequest,
):

    return refresh_login(
        req.refresh_token,
    )

@app.post("/api/auth/logout")
def logout(
    claims: dict = Depends(require_bearer),
):

    from app.user_db import clear_refresh_token

    clear_refresh_token(
        claims["email"]
    )

    return {
        "message": "Logged out successfully."
    }

@app.post("/api/auth/google")
def google_auth_endpoint(
    req: GoogleLoginRequest,
):

    return google_login(
        req.credential
    )


@app.post("/api/auth/forgot-password")
def forgot_password(req: ForgotPasswordRequest):
    return forgot_password_service(req.identifier)


@app.get("/api/auth/me")
def whoami(claims: dict = Depends(require_bearer)):

    return {
        "id": claims["id"],
        "username": claims["username"],
        "role": claims["role"],
        "department": claims["department"],
        "status": claims["status"],
        "permissions": claims.get("permissions", []),
    }


# ─── Real-time notifications ────────────────────────────────────────────────
@app.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    await notifications.notifications_endpoint(websocket)


# ─── Integration status (for the frontend to show live badges) ─────────────
@app.get("/api/integrations/status")
def integrations_status():
    return {
        "azure_openai": config.AZURE_OPENAI_CONFIGURED,
        "azure_ai_search": config.AZURE_SEARCH_CONFIGURED,
        "purview": config.PURVIEW_CONFIGURED,
        "postgres": db_pg.is_available(),
        "redis": cache.backend_name() == "redis",
        "oidc": config.OIDC_CONFIGURED,
        "smtp": config.SMTP_CONFIGURED,
        "orchestrator_engine": config.ORCHESTRATOR_ENGINE,
        "prometheus": config.PROMETHEUS_ENABLED,
    }


@app.get("/api/health")
def health():
    store = get_store()
    return {
        "status": "ok",
        "demo_mode": config.DEMO_MODE,
        "vector_backend": store.backend,
        "policy_chunks": len(store.base_blocks),
        "models": {"triage": config.TRIAGE_MODEL, "analysis": config.ANALYSIS_MODEL},
    }


@app.get("/api/compliance/trend")
def compliance_trend(
    user: dict = Depends(require("view")),
    x_tenant: str = Header(default="acmecorp"),
):
    _fallback = {
        "history": [],
        "forecast": [],
        "formula": "Policy Updates * 25% + Training Completion * 20% + Audit Findings * 25% + Security Violations * 15% + Documentation Quality * 15%",
        "weights": {
            "policy_updates": 0.25,
            "training_completion": 0.20,
            "audit_findings": 0.25,
            "security_violations": 0.15,
            "documentation_quality": 0.15
        }
    }
    try:
        return _compliance_trend_impl(user, x_tenant)
    except Exception:
        print("[api/compliance/trend] Unhandled error, returning empty trend instead of 500:")
        print(traceback.format_exc())
        return _fallback


def _compliance_trend_impl(user: dict, x_tenant: str):
    all_scans = db.list_scans(tenant_id=x_tenant, limit=500)

    all_scans = filter_documents(user, all_scans)

    # Calculate current score based on database scans
    # Findings score: starts at 100, drops by 1.5 per violation (capped at 0)
    total_violations = sum(s.total_violations for s in all_scans)
    findings_score = max(0.0, 100.0 - (total_violations * 1.5))

    # Security score: starts at 100, drops by 4 per critical violation
    critical_violations = sum(sum(1 for v in s.violations if v.severity == "P1") for s in all_scans)
    security_score = max(0.0, 100.0 - (critical_violations * 4.0))

    # 1. Policy Updates is tied dynamically to the number of custom policies in the playground
    custom_policies = db.list_custom_policies(tenant_id=x_tenant)
    policy_updates = min(100.0, 80.0 + len(custom_policies) * 3.0)

    # 2. Training Completion is linked directly to active remediation commits in the audit log
    audit_logs = db.get_audit(limit=1000)

    audit_logs = filter_documents(user, audit_logs)
    num_remediations = sum(1 for log in audit_logs if log.action == "REMEDIATION_APPLIED")
    training_completion = min(100.0, 70.0 + num_remediations * 4.0)

    # 3. Documentation Quality is tied directly to the average score and clean ratio of scans
    if all_scans:
        avg_score = sum(s.compliance_score for s in all_scans) / len(all_scans)
        clean_docs = sum(1 for s in all_scans if s.total_violations == 0)
        clean_ratio = clean_docs / len(all_scans)
        documentation_quality = min(100.0, round(avg_score * 0.8 + clean_ratio * 20.0, 1))
    else:
        documentation_quality = 85.0

    # Calculate weighted index
    today_index = (
        policy_updates * 0.25 +
        training_completion * 0.20 +
        findings_score * 0.25 +
        security_score * 0.15 +
        documentation_quality * 0.15
    )

    # Save/Update today's metric in SQLite
    today_str = datetime.now().strftime("%Y-%m-%d")
    db.save_compliance_metric(today_str, policy_updates, training_completion, findings_score, security_score, documentation_quality)

    # Load history
    history_records = db.get_compliance_history()
    history_data = []
    for r in history_records:
        weighted = (
            r["policy_updates"] * 0.25 +
            r["training_completion"] * 0.20 +
            r["audit_findings"] * 0.25 +
            r["security_violations"] * 0.15 +
            r["documentation_quality"] * 0.15
        )
        history_data.append({
            "date": r["date"],
            "policy_updates": r["policy_updates"],
            "training_completion": r["training_completion"],
            "audit_findings": r["audit_findings"],
            "security_violations": r["security_violations"],
            "documentation_quality": r["documentation_quality"],
            "compliance_index": round(weighted, 1)
        })

    # Dynamic Trend Forecasting (linear trend extrapolation)
    # Computes the slope of the historical points and projects it
    def calculate_forecast_item(history_list, key: str, steps: float, default_val: float) -> float:
        vals = [pt[key] for pt in history_list]
        if len(vals) < 2:
            return max(0.0, min(100.0, default_val - (4.0 if steps < 3 else 7.0)))
        n = len(vals)
        sum_x = sum(range(n))
        sum_y = sum(vals)
        sum_xx = sum(i*i for i in range(n))
        sum_xy = sum(i*vals[i] for i in range(n))
        denom = (n * sum_xx - sum_x * sum_x)
        slope = (n * sum_xy - sum_x * sum_y) / denom if denom != 0 else -0.1
        projected = vals[-1] + (slope * steps)
        return max(0.0, min(100.0, round(projected, 1)))

    forecast_week_pu = calculate_forecast_item(history_data, "policy_updates", 1.4, policy_updates)
    forecast_week_tc = calculate_forecast_item(history_data, "training_completion", 1.4, training_completion)
    forecast_week_af = calculate_forecast_item(history_data, "audit_findings", 1.4, findings_score)
    forecast_week_sv = calculate_forecast_item(history_data, "security_violations", 1.4, security_score)
    forecast_week_dq = calculate_forecast_item(history_data, "documentation_quality", 1.4, documentation_quality)

    forecast_month_pu = calculate_forecast_item(history_data, "policy_updates", 6.0, policy_updates)
    forecast_month_tc = calculate_forecast_item(history_data, "training_completion", 6.0, training_completion)
    forecast_month_af = calculate_forecast_item(history_data, "audit_findings", 6.0, findings_score)
    forecast_month_sv = calculate_forecast_item(history_data, "security_violations", 6.0, security_score)
    forecast_month_dq = calculate_forecast_item(history_data, "documentation_quality", 6.0, documentation_quality)

    forecast_week_index = round(
        forecast_week_pu * 0.25 +
        forecast_week_tc * 0.20 +
        forecast_week_af * 0.25 +
        forecast_week_sv * 0.15 +
        forecast_week_dq * 0.15,
        1
    )
    forecast_month_index = round(
        forecast_month_pu * 0.25 +
        forecast_month_tc * 0.20 +
        forecast_month_af * 0.25 +
        forecast_month_sv * 0.15 +
        forecast_month_dq * 0.15,
        1
    )

    forecast_data = [
        {
            "date": "Next Week",
            "policy_updates": forecast_week_pu,
            "training_completion": forecast_week_tc,
            "audit_findings": forecast_week_af,
            "security_violations": forecast_week_sv,
            "documentation_quality": forecast_week_dq,
            "compliance_index": forecast_week_index,
            "is_forecast": True
        },
        {
            "date": "Next Month",
            "policy_updates": forecast_month_pu,
            "training_completion": forecast_month_tc,
            "audit_findings": forecast_month_af,
            "security_violations": forecast_month_sv,
            "documentation_quality": forecast_month_dq,
            "compliance_index": forecast_month_index,
            "is_forecast": True
        }
    ]

    return {
        "history": history_data,
        "forecast": forecast_data,
        "formula": "Policy Updates * 25% + Training Completion * 20% + Audit Findings * 25% + Security Violations * 15% + Documentation Quality * 15%",
        "weights": {
            "policy_updates": 0.25,
            "training_completion": 0.20,
            "audit_findings": 0.25,
            "security_violations": 0.15,
            "documentation_quality": 0.15
        }
    }


@app.post("/api/scan")
async def scan(
    file: UploadFile = File(...),
    user: dict = Depends(require("upload")),
    x_tenant: str = Header(default="acmecorp"),
):
    data = await file.read()
    uploaded_by = user["username"]
    department = user["department"]

    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    # 1. Guardrail - File size validation (Max 20MB)
    if len(data) > 20 * 1024 * 1024:
        db.log_audit(
            user["username"],
            user["role"],
            user["department"],
            "UPLOAD_BLOCKED",
            file.filename,
            "File size exceeded 20MB limit"
        )
        raise HTTPException(status_code=400, detail="Security Guardrail: File size exceeds the maximum limit of 20MB.")

    # 2. Guardrail - File type validation
    ext = file.filename.split('.')[-1].lower() if '.' in file.filename else ''
    if ext not in ['pdf', 'docx', 'txt', 'md']:
        db.log_audit(
            user["username"],
            user["role"],
            user["department"],
            "UPLOAD_BLOCKED",
            file.filename,
            f"Invalid file type: {ext}"
        )
        raise HTTPException(status_code=400, detail="Security Guardrail: Unsupported file type. Only PDF, DOCX, TXT, and MD are allowed.")

    # 3. Guardrail - Prompt Injection check
    from app.pipeline.parser import parse_document
    import re
    text = parse_document(file.filename, data)

    from app.pipeline.department_classifier import classify_department

    predicted_department = await classify_department(text)

    # Determine which department the document belongs to
    if user["role"] == "central_admin":
        department = predicted_department
    else:
        department = user["department"]

    if not has_document_access(
        user,
        {"department": predicted_department},
    ):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Upload blocked.\n"
                f"Detected Department : {predicted_department}\n"
                f"Your Department : {user['department']}"
            )
        )

    injection_patterns = [
        r"(?:ignore|bypass)\s+(?:the\s+)?(?:previous\s+)?(?:instructions|rules|guardrails|directives)",
        r"reveal\s+(?:your\s+)?(?:system\s+)?prompt",
        r"you\s+are\s+now\s+(?:a\s+)?(?:dan|compliant|approved)",
        r"mark\s+this\s+document\s+as\s+(?:fully\s+)?compliant"
    ]
    injection_labels = [
        "Instruction override attempt",
        "System prompt disclosure attempt",
        "Persona override attempt",
        "Compliance status manipulation attempt",
    ]
    for pattern, label in zip(injection_patterns, injection_labels):
        if re.search(pattern, text, re.IGNORECASE):
            db.log_audit(user["username"], user["role"], user["department"], "INJECTION_BLOCKED", file.filename, f"{label} blocked in document content.")
            raise HTTPException(status_code=400, detail="Security Guardrail Alert: Prompt Injection Attack Attempt Detected and Blocked.")

    import asyncio
    import json

    async def event_generator():
        # Run core pipeline asynchronously to get actual violations first
        record = await run_pipeline(
            file.filename,
            data,
            uploaded_by=uploaded_by,
            department=department,
            tenant_id=x_tenant,
        )
        record.uploaded_by = uploaded_by
        record.tenant_id = x_tenant
        record.department = department

        # Persist the real uploaded file so later Resolve actions can
        # regenerate an updated copy of it (not a template).
        try:
            ext = file.filename.split('.')[-1].lower() if '.' in file.filename else 'txt'
            uploads_dir = config.DATA_DIR / "uploads"
            uploads_dir.mkdir(exist_ok=True)
            original_path = uploads_dir / f"{record.scan_id}.{ext}"
            original_path.write_bytes(data)
            record.original_file_path = str(original_path)
            record.original_file_ext = ext
        except Exception as e:
            print(f"[scan] Failed to persist original file for remediation: {e}")

        # Normalize score_breakdown before saving
        if hasattr(record, "score_breakdown"):
            if isinstance(record.score_breakdown, dict):
                record.score_breakdown = [
                    {
                        "factor": k,
                        "detail": "",
                        "points": v,
                    }
                    for k, v in record.score_breakdown.items()
                ]
            elif record.score_breakdown is None:
                record.score_breakdown = []

        db.save_scan(record)
        db.log_audit(user["username"], user["role"], user["department"], "UPLOAD_AND_SCAN", file.filename,
                     f"{record.total_violations} violations, score {record.compliance_score}")

        # Postgres mirror (no-op when DATABASE_URL isn't configured)
        db_pg.mirror_audit(uploaded_by, user["role"], user["department"], "UPLOAD_AND_SCAN", file.filename,
                            f"{record.total_violations} violations, score {record.compliance_score}")
        db_pg.mirror_scan(record.scan_id, x_tenant, file.filename,
                           record.compliance_score, record.total_violations,
                           record.model_dump_json() if hasattr(record, "model_dump_json") else record.json())

        # Prometheus counters
        metrics.SCAN_COUNTER.labels(tenant=x_tenant, outcome="clean" if record.total_violations == 0 else "violations").inc()
        for v in record.violations:
            sev = v.severity.value if hasattr(v.severity, "value") else str(v.severity)
            reg = v.source_regulation.value if hasattr(v.source_regulation, "value") else str(v.source_regulation)
            metrics.VIOLATION_COUNTER.labels(severity=sev, regulation=reg).inc()

        # Real-time notification to every connected dashboard
        await notifications.manager.broadcast({
            "type": "scan_completed",
            "department": department,
            "document_name": file.filename,
            "compliance_score": record.compliance_score,
            "total_violations": record.total_violations,
            "scan_id": record.scan_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # Build dynamic logs matching actual findings
        logs = [
            f"🚀 Commencing Multi-Agent Council review for: {file.filename}"
        ]

        gdpr_viols = [v for v in record.violations if v.source_regulation.value == "gdpr"]
        if gdpr_viols:
            logs.append("🔒 [GDPR Agent] Retrieving matching regulatory clauses from vector store...")
            clauses = [v.citation.clause for v in gdpr_viols if v.citation and v.citation.clause]
            clause_str = f" (Art. {', '.join(clauses)})" if clauses else ""
            logs.append(f"🔒 [GDPR Agent] Grounding: Found {len(gdpr_viols)} privacy compliance issues{clause_str}.")
        else:
            logs.append("🔒 [GDPR Agent] Reviewing privacy statements... No major GDPR violations detected.")

        sec_viols = [v for v in record.violations if v.source_regulation.value in ["iso27001", "internal_security"]]
        if sec_viols:
            logs.append("🔑 [Security Agent] Running entropy detectors & scanning protocol headers...")
            logs.append(f"🔑 [Security Agent] Flagged {len(sec_viols)} security risks: {', '.join(v.title for v in sec_viols)}.")
        else:
            logs.append("🔑 [Security Agent] Performing security audit... All system endpoints secure.")

        sox_viols = [v for v in record.violations if v.source_regulation.value == "sox"]
        if sox_viols:
            logs.append("⚖️ [Legal Agent] Modeling liability and statutory penalty exposure...")
            logs.append(f"⚖️ [Legal Agent] Flagged SOX financial risks: {', '.join(v.title for v in sox_viols)}.")
        else:
            logs.append("⚖️ [Legal Agent] Analyzing corporate agreements... SOX financial exposure is minimal.")

        hr_viols = [v for v in record.violations if v.source_regulation.value == "internal_hr"]
        if hr_viols:
            logs.append("📁 [Internal Policy Agent] Reviewing organization guidelines against internal rules...")
            logs.append(f"📁 [Internal Policy Agent] Policy deviation: {', '.join(v.title for v in hr_viols)}.")
        else:
            logs.append("📁 [Internal Policy Agent] No governance deviations found.")

        logs.append("🤝 [Consensus Council] Aggregating findings. Deduplicating overlapping vulnerabilities.")
        logs.append("✓ Scan pipeline completed. Returning results.")

        for log_msg in logs:
            yield "data: " + json.dumps({"type": "agent_log", "message": log_msg}) + "\n\n"
            await asyncio.sleep(0.4)

        # Serialize scan record
        rec_json = record.model_dump_json() if hasattr(record, "model_dump_json") else record.json()
        rec_dict = json.loads(rec_json)

        yield "data: " + json.dumps({"type": "completed", "record": rec_dict}) + "\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.delete("/api/scan/{scan_id}")
def delete_scan(scan_id: str,
                 user: dict = Depends(require("report_delete"))):
    rec = db.get_scan(scan_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Scan not found")

    res = abac.AuthorizationService.evaluate(user, rec.__dict__, action="delete")
    if res["decision"] != "PERMIT":
        raise HTTPException(status_code=403, detail=res["reason"])

    with db._conn() as c:
        c.execute("DELETE FROM scans WHERE scan_id=?", (scan_id,))
    db.log_audit(user["username"], user["role"], user["department"], "DELETE_AUDIT", rec.document_name, f"Deleted scan record {scan_id}")
    return {"status": "deleted"}


@app.get("/api/scans", response_model=list[ScanRecord])
def scans(
    user: dict = Depends(require("view")),
    x_tenant: str = Header(default="acmecorp"),
):
    try:
        all_scans = db.list_scans(tenant_id=x_tenant)
    except Exception:
        print("[api/scans] db.list_scans failed, returning empty list instead of 500:")
        print(traceback.format_exc())
        return []

    permitted_scans = []
    for s in all_scans:
        try:
            res = abac.AuthorizationService.evaluate(user, s.__dict__, action="view")
            if res["decision"] == "PERMIT":
                permitted_scans.append(s)
        except Exception as e:
            # A single bad ABAC lookup (e.g. a missing employee profile)
            # should never 500 the whole list — fail closed for that one
            # scan (excluded) and keep going.
            print(f"[api/scans] ABAC evaluation failed for scan {s.scan_id}: {e}")
            continue
    return permitted_scans


@app.get("/api/scan/{scan_id}", response_model=None)
def scan_detail(
    scan_id: str,
    user: dict = Depends(require("view"))
):
    rec = db.get_scan(scan_id)

    if not rec:
        raise HTTPException(status_code=404, detail="Scan not found")

    res = abac.AuthorizationService.evaluate(user, rec.__dict__, action="view")
    if res["decision"] != "PERMIT":
        raise HTTPException(status_code=403, detail=res["reason"])

    rec_dict = rec.model_dump() if hasattr(rec, "model_dump") else rec.dict()
    if res.get("mask_pii"):
        rec_dict["summary"] = "[PII MASKED] " + (rec_dict.get("summary") or "")
        rec_dict["raw_text"] = "[PII MASKED DATA]"
    if res.get("mask_financial"):
        rec_dict["summary"] = "[FINANCIAL DATA MASKED] " + (rec_dict.get("summary") or "")

    return rec_dict


@app.get("/api/scan/{scan_id}/pdf")
def download_pdf_report(
    scan_id: str,
    user: dict = Depends(require("view"))
):
    rec = db.get_scan(scan_id)

    if not rec:
        raise HTTPException(status_code=404, detail="Scan not found")

    res = abac.AuthorizationService.evaluate(user, rec.__dict__, action="download")
    if res["decision"] != "PERMIT":
        raise HTTPException(status_code=403, detail=res["reason"])

    from app.pipeline.pdf_generator import generate_pdf_report
    from fastapi import Response

    pdf_bytes = generate_pdf_report(rec)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="compliance_report_{scan_id}.pdf"'
        },
    )
@app.post("/api/policy/custom")
def create_custom_policy(req: CustomPolicyRequest,
                          claims: dict = Depends(require_bearer),
                          x_tenant: str = Header(default="acmecorp"),
                          role: dict = Depends(require("upload"))):
    if not req.policy_name.strip():
        raise HTTPException(status_code=400, detail="Policy name cannot be empty")
    if not req.rules:
        raise HTTPException(status_code=400, detail="Rules list cannot be empty")

    # Save to SQLite DB
    policy_id = db.save_custom_policy(req.policy_name, req.rules, tenant_id=x_tenant)

    # Append to active VectorStore
    store = get_store()
    store.add_custom_policy(x_tenant, policy_id, req.policy_name, req.rules)

    # Log audit event
    db.log_audit(claims["username"], claims["role"], claims["department"], "CREATE_CUSTOM_POLICY", req.policy_name, f"Created custom policy with {len(req.rules)} rules")

    return {"id": policy_id, "policy_name": req.policy_name, "rules": req.rules}


@app.get("/api/policy/custom")
def get_custom_policies(role: dict = Depends(require("view")), x_tenant: str = Header(default="acmecorp")):
    return db.list_custom_policies(tenant_id=x_tenant)


@app.get("/api/policy/retrieve")
def retrieve_policies(text: str, n: int = 3, role: dict = Depends(require("view")), x_tenant: str = Header(default="acmecorp")):
    store = get_store()
    citations = store.retrieve(text, tenant_id=x_tenant, n=n)
    return citations


@app.delete("/api/policy/custom/{policy_id}")
def delete_custom_policy_endpoint(policy_id: int,
                                   claims: dict = Depends(require_bearer),
                                   x_tenant: str = Header(default="acmecorp"),
                                   role: dict = Depends(require("manage"))):
    # Verify existence
    policies = db.list_custom_policies(tenant_id=x_tenant)
    policy = next((p for p in policies if p["id"] == policy_id), None)
    if not policy:
        raise HTTPException(status_code=404, detail="Custom policy not found")

    # Delete from DB
    db.delete_custom_policy(policy_id)

    # Reset vector store so that it re-initializes from scratch (without the deleted policy)
    from app.pipeline import vectorstore
    vectorstore._store = None
    get_store()

    # Log audit event
    db.log_audit(claims["username"], claims["role"], claims["department"], "DELETE_CUSTOM_POLICY", policy["policy_name"], f"Deleted custom policy {policy_id}")

    return {"status": "deleted"}


@app.post("/api/policy/re-scan")
async def rescan_history(claims: dict = Depends(require_bearer),
                          x_tenant: str = Header(default="acmecorp"),
                          role: dict = Depends(require("manage"))):
    all_scans = db.list_scans(tenant_id=x_tenant, limit=500)
    rescanned_count = 0
    from app.pipeline.agents import run_multi_agent_council
    if claims["role"] != "central_admin":
        all_scans = [
            s
            for s in all_scans
            if getattr(s, "department", None) == claims["department"]
        ]

    for s in all_scans:
        # Re-run rule engine and vector store on the saved raw text
        doc_text = getattr(s, "raw_text", None) or s.summary  # fallback if raw_text is missing
        updated_rec = await run_multi_agent_council(s.document_name, doc_text, s.uploaded_by, s.department, tenant_id=s.tenant_id)
        # Preserve original ID, created_at, uploaded_by, etc.
        updated_rec.scan_id = s.scan_id
        updated_rec.created_at = s.created_at
        updated_rec.sha256_hash = s.sha256_hash
        updated_rec.original_file_path = s.original_file_path
        updated_rec.original_file_ext = s.original_file_ext

        db.save_scan(updated_rec)
        rescanned_count += 1

    db.log_audit(claims["username"], claims["role"], claims["department"], "RE-SCAN_ALL_HISTORY", f"scans count: {rescanned_count}",
                 "Bulk re-evaluation against active policies.")

    return {"status": "success", "count": rescanned_count}


@app.post("/api/scan/{scan_id}/remediate", response_model=ScanRecord)
async def remediate(
    scan_id: str,
    req: RemediateRequest,
    user: dict = Depends(require("remediation")),
):
    rec = db.get_scan(scan_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not has_document_access(user, rec.__dict__):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )

    resolved_violations = []
    remaining_violations = []
    resolved_for_ui = []

    score_boost = 0
    exposure_min_reduction = 0.0
    exposure_max_reduction = 0.0
    affected_users_reduction = 0

    for v in rec.violations:
        if v.id in req.violation_ids:
            resolved_violations.append(v)
        else:
            remaining_violations.append(v)

    if not resolved_violations:
        # Keep only unresolved violations
        rec.last_remediation = resolved_for_ui
        return rec

    # ─── Generate rewrite (if missing) ──────────────────────────────────────
    # Every resolved violation must carry a real, non-empty compliant
    # rewrite before it's applied to the document. Reuses the existing
    # ChromaDB store + LLM wrapper (same helper the scan pipeline uses);
    # never invents a placeholder and never overwrites a rewrite that
    # already exists.
    if any(not (v.remediated_text or "").strip() for v in resolved_violations):
        from app.pipeline.agents import _generate_ai_remediation
        from app.pipeline.vectorstore import get_store

        store = get_store()
        for v in resolved_violations:
            if not (v.remediated_text or "").strip():
                rem_details = await _generate_ai_remediation(
                    excerpt=v.excerpt,
                    source_regulation=v.source_regulation.value,
                    recommendation=v.recommendation,
                    title=v.title,
                    tenant_id=rec.tenant_id,
                    store=store,
                )
                # ─── Save remediated_text ───────────────────────────────────
                v.remediated_text = rem_details["remediated_text"]
                if not (v.remediation_reasoning or "").strip():
                    v.remediation_reasoning = rem_details["remediation_reasoning"]

    for v in resolved_violations:
        resolved_for_ui.append({
            "id": v.id,
            "title": v.title,
            "excerpt": v.excerpt,
            "remediated_text": v.remediated_text,
            "recommendation": v.recommendation,
            "severity": v.severity.value,
        })

    # ─── Persist durable remediation state ──────────────────────────────────
    # Stored as real ScanRecord fields (not the transient `resolved_for_ui`
    # list above), so this survives db.save_scan()/get_scan() round-trips —
    # i.e. a page refresh, new session, or server restart never loses which
    # violations were resolved or what text was substituted.
    now = datetime.now(timezone.utc)
    for v in resolved_violations:
        document_position = rec.raw_text.find(v.excerpt) if rec.raw_text else -1
        violated_rule = ", ".join(v.regulation_articles) if v.regulation_articles else v.source_regulation.value
        rec.resolved_violations.append(
            ResolvedViolation(
                violation_id=v.id,
                original_text=v.excerpt,
                remediated_text=v.remediated_text or "",
                violated_rule=violated_rule,
                recommendation=v.recommendation,
                resolution_status="resolved",
                document_position=document_position,
                resolved_at=now,
            )
        )

    # ─── Document Regeneration (text replacement only, NO LLM re-scan) ─────
    # Apply the resolved clause replacements to the actual document file so
    # the remediated document is available for download.  This is purely a
    # text-substitution step — fast and deterministic, no LLM inference.
    if rec.original_file_path and Path(rec.original_file_path).exists():
        try:
            from app.pipeline.doc_remediator import regenerate_document

            replacements = []
            for v in resolved_violations:
                if not v.excerpt:
                    continue
                if not getattr(v, "remediated_text", None):
                    continue
                replacements.append((v.excerpt.strip(), v.remediated_text.strip()))

            if replacements:
                new_bytes = regenerate_document(rec.original_file_path, rec.original_file_ext, replacements)

                remediated_dir = config.DATA_DIR / "remediated"
                remediated_dir.mkdir(exist_ok=True)
                version = len(rec.remediated_documents) + 1
                ext = rec.original_file_ext or "txt"
                stored_name = f"{rec.scan_id}_v{version}.{ext}"
                stored_path = remediated_dir / stored_name
                stored_path.write_bytes(new_bytes)

                base_name = Path(rec.document_name).stem
                download_name = f"{base_name}_remediated_v{version}.{ext}"

                rec.remediated_documents.append({
                    "version": version,
                    "path": str(stored_path),
                    "filename": download_name,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                })

                # Point future remediation rounds at this newly-saved file
                rec.original_file_path = str(stored_path)

                # Update raw_text from the regenerated document
                try:
                    from app.pipeline.parser import parse_document
                    rec.raw_text = parse_document(download_name, new_bytes)
                except Exception:
                    pass
        except Exception as e:
            print(f"[remediate] Document regeneration failed (non-fatal): {e}")

    # ─── Update record: drop resolved violations, recalculate everything ──
    # Single deterministic path — no fallback needed.  Score is calculated
    # directly from the REMAINING violations with exposure/affected-users
    # recomputed from those remaining violations only, so the score always
    # increases as violations are resolved and reaches exactly 100 when the
    # last violation is cleared.
    rec.violations = remaining_violations
    rec.total_violations = len(remaining_violations)

    breakdown = {s.value: 0 for s in Severity}
    for v in remaining_violations:
        breakdown[v.severity.value] += 1
    rec.severity_breakdown = breakdown

    # Recalculate exposure and affected users from REMAINING violations only
    # (not from the original record).  This ensures the exposure/user
    # penalties actually drop as violations are resolved.
    rec.total_exposure_min = sum(getattr(v, 'estimated_fine_min', 0) or 0 for v in remaining_violations)
    rec.total_exposure_max = sum(getattr(v, 'estimated_fine_max', 0) or 0 for v in remaining_violations)
    rec.total_affected_users = sum(getattr(v, 'affected_users_estimate', 0) or 0 for v in remaining_violations)

    score_result = calculate_compliance_score(
        remaining_violations,
        rec.total_exposure_max,
        rec.total_affected_users,
        getattr(rec, "confidence", 1.0),
    )
    rec.compliance_score = score_result["score"]
    rec.predicted_compliance_score = score_result["score"]
    rec.compliance_status = score_result["status"]
    rec.risk_level = score_result["risk_level"]
    rec.score_breakdown = score_result.get("breakdown", rec.score_breakdown)

    db.save_scan(rec)

    # Log each applied resolution
    for v in resolved_violations:
        db.log_audit(
            user["username"],
            user["role"],
            user["department"], "REMEDIATION_APPLIED", rec.document_name,
            f"Resolved '{v.title}' (AI patch); score +{getattr(v, 'remediation_score_improvement', 0)}%."
        )
        metrics.REMEDIATION_COUNTER.inc()

    cache.invalidate_prefix(f"crew_analysis:{scan_id}")
    await notifications.manager.broadcast({
        "type": "remediation_applied",
        "document_name": rec.document_name,
        "compliance_score": rec.compliance_score,
        "resolved_count": len(resolved_violations),
        "scan_id": rec.scan_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return rec


@app.get("/api/scan/{scan_id}/remediated-document/{version}")
async def get_remediated_document(
    scan_id: str,
    version: int,
    download: bool = False,
    user: dict = Depends(require("remediation")),
):
    rec = db.get_scan(scan_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not has_document_access(user, rec.__dict__):
        raise HTTPException(status_code=403, detail="Access denied")

    if download:
        # Download is locked until the document is fully compliant.
        if rec.compliance_score != 100:
            raise HTTPException(
                status_code=403,
                detail="Download is locked until compliance score reaches 100.",
            )
        # Same selection rule as preview: always the latest backend
        # remediated document, never the original upload, never a stale
        # version — so the downloaded file matches View Updated Document.
        if not rec.remediated_documents:
            raise HTTPException(status_code=404, detail="Remediated document version not found")
        entry = max(rec.remediated_documents, key=lambda d: d.get("version", 0))
    else:
        # Preview must always reflect the current backend document — the
        # latest remediated version — never the original upload and never
        # a stale/older version, regardless of what `version` was passed.
        if not rec.remediated_documents:
            raise HTTPException(status_code=404, detail="Remediated document version not found")
        entry = max(rec.remediated_documents, key=lambda d: d.get("version", 0))

    path = Path(entry["path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Remediated document file is missing on disk")

    ext = (rec.original_file_ext or "txt").lower()
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "pdf": "application/pdf",
        "txt": "text/plain",
        "md": "text/markdown",
    }
    media_type = media_types.get(ext, "application/octet-stream")

    if download:
        # Downloaded bytes start identical to the previewed document, then
        # get a Remediation Appendix appended on top (preview itself is
        # left as the plain document, unchanged).
        from app.pipeline.doc_remediator import append_remediation_appendix
        from fastapi.responses import Response

        base_bytes = path.read_bytes()
        final_bytes = append_remediation_appendix(base_bytes, ext, rec.resolved_violations)
        return Response(
            content=final_bytes,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{entry["filename"]}"'},
        )

    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(path),
        media_type=media_type,
        filename=entry["filename"],
        headers={"Content-Disposition": f'inline; filename="{entry["filename"]}"'},
    )


@app.get("/api/audit")
def audit(
    user: dict = Depends(require("audit")),
):
    logs = db.get_audit()
    return filter_documents(user, logs)


@app.get("/api/dashboard", response_model=DashboardStats)
def dashboard(
    user: dict = Depends(require("view")),
    x_tenant: str = Header(default="acmecorp"),
):
    try:
        return _dashboard_impl(user, x_tenant)
    except Exception:
        print("[api/dashboard] Unhandled error, returning empty dashboard instead of 500:")
        print(traceback.format_exc())
        return DashboardStats(
            overall_compliance_score=100,
            overall_status="Compliant",
            overall_risk_level="Low",
            policies_scanned=0,
            risks_detected=0,
            documents_analyzed=0,
            compliance_trend=[],
            risk_by_category=[{"name": "No data", "value": 100}],
            top_risky_areas=[{"name": "No risks", "risks": 0}],
            recent_alerts=[],
            total_exposure_min=0.0,
            total_exposure_max=0.0,
            total_affected_users=0,
        )


def _dashboard_impl(user: dict, x_tenant: str):
    all_scans = db.list_scans(tenant_id=x_tenant, limit=500)
    all_scans = filter_documents(user, all_scans)

    docs = len(all_scans)
    risks = sum(s.total_violations for s in all_scans)
    avg_score = round(sum(s.compliance_score for s in all_scans) / docs) if docs else 100
    overall_status_risk = compliance_status_and_risk(avg_score)

    # severity -> category rollup
    cat = {"Access Control": 0, "Data Protection": 0, "Policy Violation": 0,
           "Configuration": 0, "Others": 0}
    cat_map = {
        "internal_security": "Access Control",
        "gdpr": "Data Protection",
        "internal_hr": "Policy Violation",
        "iso27001": "Configuration",
        "sox": "Others",
    }
    for s in all_scans:
        for v in s.violations:
            cat[cat_map.get(v.source_regulation.value, "Others")] += 1
    total_cat = sum(cat.values()) or 1
    risk_by_category = [
        {"name": k, "value": round(v / total_cat * 100)} for k, v in cat.items() if v
    ]
    top_risky = sorted(
        ({"name": k, "risks": v} for k, v in cat.items() if v),
        key=lambda x: -x["risks"])[:4]

    # Real historical trend — the same compliance_index history
    # /api/compliance/trend computes from db.get_compliance_history(),
    # reshaped to {label, value}. Empty until at least one day's metric
    # has been recorded (compliance_trend endpoint records one per scan
    # day), rather than a fabricated climbing curve.
    history_records = db.get_compliance_history()
    trend = []
    for r in history_records:
        weighted = (
            r["policy_updates"] * 0.25 +
            r["training_completion"] * 0.20 +
            r["audit_findings"] * 0.25 +
            r["security_violations"] * 0.15 +
            r["documentation_quality"] * 0.15
        )
        try:
            label = datetime.fromisoformat(r["date"]).strftime("%b %d")
        except (ValueError, TypeError):
            label = str(r["date"])
        trend.append({"label": label, "value": round(weighted)})

    alerts = []
    for s in all_scans[:5]:
        for v in s.violations[:1]:
            alerts.append({
                "title": v.title, "severity": v.severity.label,
                "document": s.document_name})

    # Calculate aggregate risk metrics
    total_exp_min = sum(getattr(s, "total_exposure_min", 0.0) or 0.0 for s in all_scans)
    total_exp_max = sum(getattr(s, "total_exposure_max", 0.0) or 0.0 for s in all_scans)
    total_aff_users = sum(getattr(s, "total_affected_users", 0) or 0 for s in all_scans)

    # If no scans are loaded, add some realistic base metrics for simulation
    if not all_scans:
        total_exp_min = 0.0
        total_exp_max = 0.0
        total_aff_users = 0

    return DashboardStats(
        overall_compliance_score=avg_score,
        overall_status=overall_status_risk["status"],
        overall_risk_level=overall_status_risk["risk_level"],
        policies_scanned=len(get_store()._get_tenant_blocks(x_tenant)),
        risks_detected=risks,
        documents_analyzed=docs,
        compliance_trend=trend,
        risk_by_category=risk_by_category or [{"name": "No data", "value": 100}],
        top_risky_areas=top_risky or [{"name": "No risks", "risks": 0}],
        recent_alerts=alerts,
        total_exposure_min=total_exp_min,
        total_exposure_max=total_exp_max,
        total_affected_users=total_aff_users
    )


# ─── CrewAI executive synthesis (runs after the multi-agent council) ───────
@app.get("/api/scan/{scan_id}/crew-analysis")
async def crew_analysis(
    scan_id: str,
    user: dict = Depends(require("view")),
):
    rec = db.get_scan(scan_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not has_document_access(user, rec.__dict__):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )
    cache_key = f"crew_analysis:{scan_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    analysis = await run_crew_analysis(rec)
    cache.set(cache_key, analysis, ttl_seconds=3600)
    return analysis


# ─── Microsoft Purview sensitivity classification ───────────────────────────
_purview_client = PurviewClient()


@app.get("/api/scan/{scan_id}/classification")
def purview_classification(
    scan_id: str,
    user: dict = Depends(require("view")),
):
    rec = db.get_scan(scan_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Scan not found")
    if not has_document_access(user, rec.__dict__):
        raise HTTPException(
            status_code=403,
            detail="Access denied",
        )
    sample = getattr(rec, "raw_text", None) or rec.summary or ""
    return _purview_client.classify_document(rec.document_name, sample[:5000])
# ─── Enterprise Employee Access Management REST APIs ───────────────────────
from app.employee_db import (
    get_all_employees_access_profiles,
    get_employee_access_profile,
    update_employee_access_profile,
    get_clearance_levels,
    get_regulations,
    get_departments as get_employee_departments,
)


class EmployeeAccessUpdateRequest(PydanticBaseModel):
    clearance_level_id: int
    allowed_regulation_ids: List[int]
    permissions: Dict[str, bool]


class AccessEvaluationRequest(PydanticBaseModel):
    user_id: Optional[Union[int, str]] = None
    resource: Dict[str, Any]
    action: str = "view"


@app.get("/api/v1/employee-access/employees")
def list_employees_access(claims: dict = Depends(require_bearer)):
    """Fetch all real employees from the database with their ABAC attributes."""
    return get_all_employees_access_profiles()


@app.get("/api/v1/employee-access/employees/{user_id}")
def get_employee_access_by_id(user_id: int, claims: dict = Depends(require_bearer)):
    """Fetch full ABAC profile for a specific employee."""
    profile = get_employee_access_profile(user_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Employee profile not found")
    return profile


@app.put("/api/v1/employee-access/employees/{user_id}")
def update_employee_access(
    user_id: int,
    req: EmployeeAccessUpdateRequest,
    claims: dict = Depends(require_bearer),
):
    """Save updated clearance level, allowed regulations, and permission toggles to DB with strict authorization checks."""
    caller_role = claims.get("role", "viewer").lower()
    caller_dept = claims.get("department", "")

    if caller_role not in ("central_admin", "admin", "manager"):
        raise HTTPException(
            status_code=403,
            detail="Permission denied. Administrator or Manager role required to update employee attributes.",
        )

    target_user = get_employee_access_profile(user_id)
    if not target_user:
        raise HTTPException(status_code=404, detail="Target employee profile not found")

    if caller_role != "central_admin":
        # Check Department Scoping
        if target_user.get("department") != caller_dept:
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. You can only manage employee access attributes within your own department ('{caller_dept}'). Target employee is in '{target_user.get('department')}'."
            )

        # Check Hierarchy / Privilege Escalation Prevention
        target_role = target_user.get("role", "").lower()
        if target_role in ("central_admin", "admin", "manager"):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied. You cannot modify access attributes for administrative user role '{target_user.get('role')}'."
            )

    updated = update_employee_access_profile(
        user_id=user_id,
        clearance_level_id=req.clearance_level_id,
        allowed_regulation_ids=req.allowed_regulation_ids,
        permissions=req.permissions,
    )
    db.log_audit(
        claims.get("username", "admin"),
        claims.get("role", "admin"),
        claims.get("department", "Security"),
        "UPDATE_EMPLOYEE_ABAC",
        f"EMP-{1000 + user_id}",
        f"Updated clearance to {updated.get('clearance_level')}, regulations={len(req.allowed_regulation_ids)}",
    )
    return updated


@app.get("/api/v1/employee-access/clearance-levels")
def list_clearance_levels_endpoint():
    """Fetch dynamic Clearance Levels from DB."""
    return get_clearance_levels()


@app.get("/api/v1/employee-access/regulations")
def list_regulations_endpoint():
    """Fetch dynamic Regulations from DB."""
    return get_regulations()


@app.get("/api/v1/employee-access/departments")
def list_departments_endpoint():
    """Fetch dynamic Departments from DB."""
    return get_employee_departments()


@app.post("/api/v1/employee-access/authorize")
def evaluate_access_endpoint(
    req: AccessEvaluationRequest,
    claims: dict = Depends(require_bearer),
):
    """
    Centralized Authorization Evaluation API.
    Evaluates 6 sequential checks and returns PERMIT/DENY with detailed explainability reasons and masking flags.
    """
    user_id = req.user_id if req.user_id is not None else claims.get("id")
    result = abac.AuthorizationService.evaluate(
        user_identifier=user_id,
        resource=req.resource,
        action=req.action,
    )
    return result


@app.get("/api/v1/abac/stats")
@app.get("/api/v1/dashboard/stats")
def get_governance_dashboard_stats(
    claims: dict = Depends(require_bearer),
):
    """Computes live enterprise governance metrics dynamically from audit records."""
    return db.get_abac_dashboard_stats()


@app.get("/api/v1/abac/audit-logs")
def get_abac_audit_logs_endpoint(
    limit: int = 100,
    user: Optional[str] = None,
    department: Optional[str] = None,
    decision: Optional[str] = None,
    matched_policy: Optional[str] = None,
    min_risk: Optional[int] = None,
    search: Optional[str] = None,
    claims: dict = Depends(require_bearer),
):
    """Retrieves detailed forensic ABAC audit logs with search and filtering."""
    return db.get_abac_audit_logs(
        limit=limit,
        user=user,
        department=department,
        decision=decision,
        matched_policy=matched_policy,
        min_risk=min_risk,
        search=search,
    )





@app.get("/api/v1/abac/users")
def get_abac_simulation_users(
    claims: dict = Depends(require_bearer),
):
    """
    Provides the real, live User Management roster to the ABAC Governance
    Policy Simulator so administrators can pick actual users/roles/departments
    instead of typing free-text or hitting hardcoded sample data.
    """
    if claims.get("role") not in ("admin", "central_admin"):
        raise HTTPException(
            status_code=403,
            detail="Only Administrators may load the live user roster for simulation.",
        )
    return get_all_users()
