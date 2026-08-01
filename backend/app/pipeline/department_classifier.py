from __future__ import annotations

from app import config

DEPARTMENTS = [
    "Finance",
    "HR",
    "Legal",
    "Operations",
    "Security",
    "Engineering",
]


async def classify_department(text: str) -> str:
    """
    Classify an uploaded enterprise document into exactly one department.
    """

    from app.pipeline.agents import _get_llm_client

    llm = _get_llm_client(
        model=config.TRIAGE_MODEL,
        temperature=0,
        max_tokens=20,
    )

    prompt = f"""
You are classifying enterprise documents.

Choose EXACTLY ONE department.

Finance:
Budgets, payroll, accounting, invoices, taxation.

HR:
Employees, recruitment, leave, attendance, performance.

Legal:
Contracts, NDAs, agreements, litigation, governing law.

Operations:
Logistics, manufacturing, supply chain, warehouse.

Security:
Cybersecurity, firewalls, passwords, encryption, TLS,
authentication, vulnerabilities, incident response.

Engineering:
Software architecture, APIs, deployment, source code,
microservices, CI/CD.

Return ONLY the department name.

Document:

{text[:3000]}
"""

    response = await llm.ainvoke(prompt)

    result = response.content.strip()

    print("Department classifier raw output:", result)

    for dept in DEPARTMENTS:
        if dept.lower() in result.lower():
            return dept

    # The LLM didn't return one of the six real departments (e.g. it said
    # "Compliance", "General", or something off-script). Departments in
    # the user directory are exactly DEPARTMENTS above, so falling back
    # to any other string here silently orphans the document: no team's
    # users match it, and only central_admin can ever see it again.
    # Instead, fall back to a simple keyword-overlap score over the
    # document text itself so the scan always lands in one of the real
    # departments its users can actually access.
    DEPARTMENT_KEYWORDS = {
        "Finance": ["budget", "payroll", "invoice", "tax", "accounting", "expense", "revenue"],
        "HR": ["employee", "recruit", "leave", "attendance", "performance review", "onboarding", "benefits"],
        "Legal": ["contract", "nda", "agreement", "litigation", "governing law", "clause", "liability"],
        "Operations": ["logistics", "manufacturing", "supply chain", "warehouse", "inventory", "shipment"],
        "Security": ["firewall", "password", "encryption", "tls", "authentication", "vulnerability", "incident response"],
        "Engineering": ["api", "deployment", "source code", "microservice", "ci/cd", "architecture", "pipeline"],
    }
    lowered = text.lower()
    scores = {
        dept: sum(lowered.count(kw) for kw in kws)
        for dept, kws in DEPARTMENT_KEYWORDS.items()
    }
    best_dept, best_score = max(scores.items(), key=lambda kv: kv[1])
    if best_score > 0:
        return best_dept

    return "Operations"