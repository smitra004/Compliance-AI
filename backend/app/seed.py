"""
Seed demo content so the dashboard looks alive on first launch and the
live demo has known documents to scan.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from app import db
from app.pipeline.orchestrator import run_pipeline

async def seed():
    db.init_db()
    
    # Only seed if the database is currently empty to avoid wiping user scan history
    existing_scans = db.list_scans(limit=1)
    if existing_scans:
        print("Database already has records, skipping seed.")
        return


    # We define 25 documents covering all combinations of:
    # Departments: HR, Finance, Legal, Security, Operations, Engineering
    # Regulations: GDPR, ISO 27001, SOX, Internal Security, Internal HR
    # Severities: P1, P2, P3, P4
    # Status: Compliant and Non-Compliant
    
    depts = ["HR", "Finance", "Legal", "Security", "Operations", "Engineering"]
    regs = ["GDPR", "ISO27001", "SOX", "InternalPolicy"]
    
    non_compliant_text = (
        "Hey team, SUBJECT: Core Audit Logs\n"
        "api_key = [REDACTED_API_KEY]\n"
        "Please review candidate details for email test-user@domain.com and phone +1 415-555-0199.\n"
        "The salary compensation for this role is $145,000.\n"
        "Transfer all archives to US servers and retain permanently.\n"
        "Grant access to everyone over http://localhost/access."
    )
    
    compliant_text = (
        "CLASSIFICATION: Internal\n"
        "SUBJECT: Standard Operations Guidelines\n"
        "All system records are encrypted at rest and in transit. "
        "Access follows the least-privilege principle. "
        "All customer data is processed locally within EU servers. "
        "Records are retained for a maximum of 24 months, after which they are securely deleted."
    )
    
    samples = []
    idx = 0
    for dept in depts:
        for reg in regs:
            # Pair A: Created recently (offset = 1 to 5 days) - matches all date ranges
            recent_offset = 1 + (idx % 5)
            samples.append((
                f"{dept}_{reg}_Vulnerabilities_Recent_Report.txt",
                non_compliant_text,
                f"{dept.lower()}_manager@nexuszenith",
                recent_offset
            ))
            samples.append((
                f"{dept}_{reg}_Compliance_Recent_Cert.txt",
                compliant_text,
                f"{dept.lower()}_auditor@nexuszenith",
                recent_offset + 1
            ))
            
            # Pair B: Created in the past (offset = 15 to 100 days) - matches older ranges
            past_offset = 15 if idx % 3 == 0 else 45 if idx % 3 == 1 else 95
            samples.append((
                f"{dept}_{reg}_Vulnerabilities_Archive_Report.txt",
                non_compliant_text,
                f"{dept.lower()}_manager@nexuszenith",
                past_offset
            ))
            samples.append((
                f"{dept}_{reg}_Compliance_Archive_Cert.txt",
                compliant_text,
                f"{dept.lower()}_auditor@nexuszenith",
                past_offset + 2
            ))
            
            idx += 1

    from app import config
    from app.pipeline.vectorstore import get_store
    
    orig_demo = config.DEMO_MODE
    config.DEMO_MODE = True
    
    store = get_store()
    orig_retrieve = store.retrieve
    store.retrieve = lambda *args, **kwargs: []

    try:
        for name, content, user, offset in samples:
            rec = await run_pipeline(name, content.encode("utf-8"), uploaded_by=user)
            rec.created_at = datetime.now(timezone.utc) - timedelta(days=offset)
            db.save_scan(rec)
            db.log_audit(user, "reviewer", "UPLOAD_AND_SCAN", name,
                         f"{rec.total_violations} violations, score {rec.compliance_score}")
    finally:
        config.DEMO_MODE = orig_demo
        store.retrieve = orig_retrieve
        
    # Seed historical compliance metrics spaced 5 days apart
    today = datetime.now(timezone.utc)
    db.save_compliance_metric((today - timedelta(days=30)).strftime("%Y-%m-%d"), 65.0, 70.0, 60.0, 55.0, 60.0)
    db.save_compliance_metric((today - timedelta(days=25)).strftime("%Y-%m-%d"), 70.0, 75.0, 65.0, 60.0, 65.0)
    db.save_compliance_metric((today - timedelta(days=20)).strftime("%Y-%m-%d"), 72.0, 78.0, 70.0, 68.0, 70.0)
    db.save_compliance_metric((today - timedelta(days=15)).strftime("%Y-%m-%d"), 75.0, 80.0, 75.0, 72.0, 75.0)
    db.save_compliance_metric((today - timedelta(days=10)).strftime("%Y-%m-%d"), 78.0, 82.0, 78.0, 75.0, 78.0)
    db.save_compliance_metric((today - timedelta(days=5)).strftime("%Y-%m-%d"), 80.0, 85.0, 82.0, 80.0, 80.0)

    db.log_audit("sounak@nexuszenith", "admin", "LOGIN", "dashboard", "session start")
    db.log_audit("sohini@nexuszenith", "admin", "POLICY_LOAD", "gdpr+internal",
                 "policy corpus embedded into vector store")


if __name__ == "__main__":
    import asyncio
    asyncio.run(seed())
    print("Seeded demo data.")
