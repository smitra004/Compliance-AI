"""
Multi-Agent Compliance Council and Simulation Engine.
Contains specialized agents (GDPR, Security, Legal, Policy) collaborating on compliance analysis,
an Autonomous Remediation Agent suggesting rewrites, and an Executive Risk Simulator.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app import config
from app.models import (
    ScanRecord, Violation, Severity, Regulation, PolicyCitation,
    ComplianceAnalysisResult
)
from app.pipeline.rules import run_rules
from app.pipeline.vectorstore import get_store
from app.pipeline.precedence import resolve_conflicts
from app.pipeline.regmap import map_articles
from app.pipeline.scoring import calculate_compliance_score

# Every compliance agent's view of the document used to be hard-truncated to
# text[:800] (~120-150 words) before it ever reached the LLM. That meant the
# score was only ever derived from whatever happened to fall in the opening
# paragraph — content later in the document (often where the real violations
# live) was silently never analyzed at all, which is why the score could
# look disconnected from the document's actual content between runs/edits.
# This cap is generous enough to cover essentially any real policy/contract
# document in one pass while staying within the model's context window; it
# is not a per-paragraph sample, it is the actual document content.
_MAX_ANALYSIS_CHARS = 24000


def _analysis_window(text: str) -> str:
    if text is None:
        return ""
    return text[:_MAX_ANALYSIS_CHARS]


# ─── LLM CALL RESILIENCE ─────────────────────────────────────────────────────
# Groq's free/shared tier enforces fairly aggressive per-minute request and
# token limits. With several agents calling the LLM per scan, and several
# scans potentially running at once (multiple users, or the frontend's
# health-poll triggering re-renders), it's easy to burst past those limits
# and get back a 429. Two things fix that:
#
#   1. `_LLM_CONCURRENCY` — a process-wide semaphore so only a small number
#      of LLM calls are ever in flight at once, no matter how many scan
#      requests FastAPI is handling concurrently.
#   2. `_call_llm_with_retry` — wraps every `.ainvoke(...)` call with
#      exponential backoff + jitter, specifically for 429 / rate-limit
#      errors, so a transient limit hit doesn't fail the whole agent.
_LLM_MAX_CONCURRENCY = int(__import__("os").environ.get("LLM_MAX_CONCURRENCY", "1"))
_LLM_CONCURRENCY = asyncio.Semaphore(_LLM_MAX_CONCURRENCY)

_LLM_MAX_RETRIES = int(__import__("os").environ.get("LLM_MAX_RETRIES", "8"))
_LLM_BASE_BACKOFF_SECONDS = float(__import__("os").environ.get("LLM_BASE_BACKOFF_SECONDS", "3"))
_AGENT_STEP_DELAY_SECONDS = float(__import__("os").environ.get("AGENT_STEP_DELAY_SECONDS", "4"))


class _ConsensusHandled(Exception):
    """Raised internally to unwind out of the consensus block after we've
    already built a valid (per-agent) result, so the outer except doesn't
    treat it as a full pipeline failure and discard that result."""
    pass


def _is_rate_limit_error(exc: Exception) -> bool:
    """Best-effort detection of a 429 / rate-limit error across the
    different exception shapes langchain / the underlying HTTP client can
    raise (they don't all expose a clean status_code attribute)."""
    status = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
    if status == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg or "rate limit" in msg or "rate_limit" in msg or "too many requests" in msg


async def _call_llm_with_retry(llm, prompt, *, max_retries: int = None, base_delay: float = None):
    """Calls llm.ainvoke(prompt) under the global concurrency limiter, with
    exponential backoff + jitter on 429s. Non-rate-limit errors are raised
    immediately so callers' existing except-blocks still handle them."""
    import random

    max_retries = _LLM_MAX_RETRIES if max_retries is None else max_retries
    base_delay = _LLM_BASE_BACKOFF_SECONDS if base_delay is None else base_delay

    async with _LLM_CONCURRENCY:
        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                return await llm.ainvoke(prompt)
            except Exception as e:
                last_exc = e
                if not _is_rate_limit_error(e) or attempt == max_retries:
                    raise
                delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
                print(f"[LLM] 429 rate limit hit (attempt {attempt + 1}/{max_retries}); "
                      f"backing off {delay:.1f}s before retrying.")
                await asyncio.sleep(delay)
        raise last_exc




def _get_llm_client(model: str, temperature: float = 0.1, max_tokens: int = 2000, structured_output: bool = False, model_kwargs: Optional[Dict[str, Any]] = None):
    from langchain_openai import ChatOpenAI

    api_key = config.GROQ_API_KEY or config.OPENAI_API_KEY
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if api_key:
        kwargs["api_key"] = api_key

    if config.GROQ_API_KEY:
        kwargs["base_url"] = "https://api.groq.com/openai/v1"
    if model_kwargs:
        kwargs["model_kwargs"] = model_kwargs

    client = ChatOpenAI(**kwargs)
    if structured_output:
        return client.with_structured_output(ComplianceAnalysisResult)
    return client


# ─── AGENT PROMPTS ──────────────────────────────────────────────────────────
GDPR_AGENT_PROMPT = """
You are the GDPR Agent. Your focus is data privacy regulations, particularly GDPR Art. 5, 6, 9, 17, 28, 32, 33, 44.
Analyze the document for:
- Exposure of Personally Identifiable Information (PII) like names, emails, phone numbers, or addresses.
- Special category sensitive data (health, biometric, financial/salary details).
- Cross-border data transfers to jurisdictions without adequacy decisions (e.g. transfers to "US servers" without Standard Contractual Clauses).
- Insecure storage or transmission of personal data (unencrypted transit).
- Indefinite retention policies that violate the right to erasure (storage-limitation principle).

For each violation, provide a concise explanation grounded in GDPR (1-2 sentences, cite the article), a brief recommendation, and a compliant rewrite. Avoid lengthy narrative — professional and to the point.
"""

SECURITY_AGENT_PROMPT = """
You are the Security Agent. Your focus is cybersecurity, confidentiality, and network exposure (e.g. ISO 27001, internal security standards).
Analyze the document for:
- Exposed credentials, secrets, API keys, passwords, and tokens.
- Shared resources over unencrypted protocols (http://, plaintext channels).
- Overly broad access permissions (granting access to "everyone", "public", or "unrestricted access").
- Absence of encryption or hashing for stored sensitive payloads.

Provide concise, professional explanations of the security threat, remediation strategy, and code/text change — 1-2 sentences each, no lengthy narrative.
"""

LEGAL_AGENT_PROMPT = """
You are the Legal Agent. Your focus is regulatory liability, statutory exposure, breach notification delay, and legal interpretation.
Analyze the document for:
- Compliance-relevant statements violating local or global regulations.
- Absence of statutory disclosures, consent mechanisms, or legal bases.
- Actions that carry high litigation exposure (e.g. sharing salary details, undocumented processors, delayed notifications).

Explain the legal consequences, estimated financial exposure, and corrective rewrite concisely — 1-2 sentences each, professional tone.
"""

POLICY_AGENT_PROMPT = """
You are the Internal Policy Agent. Your focus is organizational governance, HR policies, and data classification frameworks.
Analyze the document for:
- Missing data classification labels (Public, Internal, Confidential, Restricted).
- Internal salary/compensation disclosure breaches.
- Process deviations from standard operating procedures.
- Inconsistencies with approved corporate retention schedules.

Explain the policy breach, governance risk, and correction concisely — 1-2 sentences each, professional tone.
"""

# ─── DEMO DYNAMIC REMEDIATION & RISK RULES ────────────────────────────────────
# Helper to perform regex-based compliant rewrites for the demo mode
def _suggest_remediation(violation_title: str, excerpt: str) -> Dict[str, Any]:
    """
    Deterministic, regex-based compliant rewrite for demo mode.

    Dispatches primarily on `violation_title`, which is always one of the
    exact `Rule.title` strings from `rules.py` (or a custom-policy title).
    This is what guarantees a fix actually resolves the specific violation
    that was flagged: excerpt-keyword sniffing alone is ambiguous whenever
    a single excerpt contains multiple trigger words (e.g. a sentence that
    mentions both "retain" and "US servers" belongs to two different
    violations with two different fixes), and some violations (like a
    missing classification label) don't contain any of their own trigger
    words in the flagged excerpt at all. Falling back to title-independent
    keyword sniffing only happens for unrecognized/custom titles.
    """
    text_lower = excerpt.lower()
    title_lower = (violation_title or "").lower()

    def _redact_emails(s: str) -> str:
        return re.sub(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[REDACTED_EMAIL_ADDRESS]", s)

    def _redact_phones(s: str) -> str:
        return re.sub(r"(\+?\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{4}", "[REDACTED_PHONE_NUMBER]", s)

    # 1. Hard-coded credential / secret
    if "credential" in title_lower or "secret exposed" in title_lower:
        match_pass = re.search(r"(password|passwd)\s*[:=]\s*(\S+)", excerpt, re.I)
        match_key = re.search(r"(api[_-]?key|token|bearer)\s*[:=]\s*(\S+)", excerpt, re.I)

        remediated = excerpt
        if match_pass:
            remediated = remediated.replace(match_pass.group(2), 'os.getenv("DATABASE_PASSWORD")')
        if match_key:
            remediated = remediated.replace(match_key.group(2), 'os.getenv("EXTERNAL_API_KEY")')

        if remediated == excerpt:
            remediated = "DB_PASSWORD = os.getenv(\"DB_PASSWORD\")\nAPI_KEY = os.getenv(\"API_KEY\")"

        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Hard-coded credentials risk system compromise; moved to environment-variable retrieval (ISO 27001 A.10).",
            "estimated_fine_min": 100000.0,
            "estimated_fine_max": 500000.0,
            "affected_users_estimate": 12,
            "operational_impact": "Severe — risk of database compromise and data exfiltration.",
            "reputation_risk_level": "Critical"
        }

    # 2. Email PII
    if "email addresses" in title_lower:
        return {
            "remediated_text": _redact_emails(excerpt),
            "remediation_reasoning": "Plain-text email is PII; masked to comply with GDPR Art. 5 (Data Minimisation).",
            "estimated_fine_min": 25000.0,
            "estimated_fine_max": 95000.0,
            "affected_users_estimate": 150,
            "operational_impact": "Medium — breach-notification duty under GDPR Art. 33 if leaked.",
            "reputation_risk_level": "High"
        }

    # 3. Phone PII
    if "phone numbers" in title_lower:
        return {
            "remediated_text": _redact_phones(excerpt),
            "remediation_reasoning": "Phone numbers are personal identifiers under GDPR; masked to prevent tracking/phishing.",
            "estimated_fine_min": 15000.0,
            "estimated_fine_max": 50000.0,
            "affected_users_estimate": 80,
            "operational_impact": "Low — limited to spam/identity risk.",
            "reputation_risk_level": "Medium"
        }

    # 4. Retention
    if "retention" in title_lower:
        remediated = re.sub(
            r"(retain|retention|keep|store)(.{0,40}?)(indefinit\w*|forever|permanent\w*|7\s*years|10\s*years|99\s*years)",
            lambda m: f"{m.group(1)}{m.group(2)}for 24 months in accordance with the corporate retention schedule",
            excerpt, flags=re.I,
        )
        if remediated == excerpt:
            remediated = "Personal data will be stored for a maximum period of 24 months, after which it is securely deleted."
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Indefinite storage violates GDPR Art. 5(1)(e); capped at a 24-month retention period.",
            "estimated_fine_min": 45000.0,
            "estimated_fine_max": 180000.0,
            "affected_users_estimate": 1250,
            "operational_impact": "High — prolonged retention increases breach liability.",
            "reputation_risk_level": "High"
        }

    # 5. Cross-border transfer
    if "cross-border transfer" in title_lower or "transfer without safeguards" in title_lower:
        remediated = re.sub(
            r"(us servers|united states|third country|offshore|overseas)",
            "secured local EU-based servers (with active Standard Contractual Clauses)",
            excerpt, flags=re.I,
        )
        if remediated == excerpt:
            remediated = excerpt + " (Transfer now covered by Standard Contractual Clauses and routed to EU-based servers.)"
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Undocumented cross-border transfer violates GDPR Art. 44; resolved to EU-based hosting.",
            "estimated_fine_min": 150000.0,
            "estimated_fine_max": 750000.0,
            "affected_users_estimate": 2500,
            "operational_impact": "Critical — subject to maximum DPA fines.",
            "reputation_risk_level": "Critical"
        }

    # 6. Compensation / Salary
    if "compensation data" in title_lower:
        remediated = re.sub(r"(\$|usd|inr|eur|₹|rs\.?)\s?\d[\d,]*(\.\d{2})?", "[REDACTED_COMPENSATION_FIGURE]", excerpt, flags=re.I)
        if remediated == excerpt:
            remediated = "Employee salary review details are archived in HR systems and not circulated."
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Compensation data is sensitive HR record; access restricted to HR stakeholders.",
            "estimated_fine_min": 10000.0,
            "estimated_fine_max": 40000.0,
            "affected_users_estimate": 1,
            "operational_impact": "Low — internal HR grievance risk only.",
            "reputation_risk_level": "Medium"
        }

    # 7. Unencrypted channel
    if "unencrypted channel" in title_lower:
        remediated = excerpt.replace("http://", "https://")
        remediated = re.sub(r"unencrypted(\s+\w+)?", lambda m: f"encrypted{m.group(1) or ''} (via TLS v1.3)", remediated, flags=re.I)
        remediated = re.sub(r"plain[\s-]?text|cleartext", "TLS-encrypted transmission", remediated, flags=re.I)
        if remediated == excerpt:
            remediated = excerpt + " (Now transmitted exclusively over TLS v1.3.)"
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Cleartext transmission breaches GDPR Art. 32; standardized on TLS v1.3.",
            "estimated_fine_min": 35000.0,
            "estimated_fine_max": 120000.0,
            "affected_users_estimate": 450,
            "operational_impact": "Medium — eavesdropping risk on unsecured networks.",
            "reputation_risk_level": "High"
        }

    # 8. Overly broad access
    if "access granted" in title_lower:
        remediated = re.sub(r"(everyone|all users|public|unrestricted|full access)", "authorized personnel assigned to specific compliance roles", excerpt, flags=re.I)
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Broad access violates least-privilege principle; restricted to authorized roles.",
            "estimated_fine_min": 50000.0,
            "estimated_fine_max": 200000.0,
            "affected_users_estimate": 950,
            "operational_impact": "High — insider-threat/leak risk on customer data.",
            "reputation_risk_level": "High"
        }

    # 9. Missing classification label — the flagged excerpt is just the
    # start of the document, so this must be title-driven, not keyword-driven.
    if "classification label" in title_lower:
        return {
            "remediated_text": "CLASSIFICATION: Internal\n\n" + excerpt,
            "remediation_reasoning": "Missing classification label, required under INT-SEC-01; labeled Internal.",
            "estimated_fine_min": 5000.0,
            "estimated_fine_max": 15000.0,
            "affected_users_estimate": 0,
            "operational_impact": "Low — policy-compliance gap, resolved via labeling.",
            "reputation_risk_level": "Low"
        }

    # 10. Informal tone
    if "informal tone" in title_lower:
        remediated = re.sub(r"\bhey\b", "Hello", excerpt, flags=re.I)
        remediated = re.sub(r"\bthanks\b", "Thank you", remediated, flags=re.I)
        remediated = re.sub(r"\bping me\b", "contact me", remediated, flags=re.I)
        remediated = re.sub(r"\bplease review\b", "please review at your earliest convenience", remediated, flags=re.I)
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Policy documents require formal corporate tone; informal phrasing replaced.",
            "estimated_fine_min": 0.0,
            "estimated_fine_max": 0.0,
            "affected_users_estimate": 0,
            "operational_impact": "Low — cosmetic/tone compliance only.",
            "reputation_risk_level": "Low"
        }

    # 11. Credit card
    if "credit card" in title_lower:
        remediated = re.sub(r"\b(?:\d[ -]*?){13,16}\b", "[REDACTED_CARD_NUMBER]", excerpt)
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Payment card data in plaintext violates PCI-DSS; replaced with a tokenised reference.",
            "estimated_fine_min": 50000.0,
            "estimated_fine_max": 250000.0,
            "affected_users_estimate": 200,
            "operational_impact": "Critical — PCI-DSS non-compliance risk.",
            "reputation_risk_level": "Critical"
        }

    # 12. PAN card
    if "pan card" in title_lower:
        remediated = re.sub(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "[REDACTED_PAN_NUMBER]", excerpt)
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "PAN numbers are critical PII under Indian data-protection rules; redacted.",
            "estimated_fine_min": 20000.0,
            "estimated_fine_max": 100000.0,
            "affected_users_estimate": 1,
            "operational_impact": "Medium — identity-theft exposure.",
            "reputation_risk_level": "High"
        }

    # 13. Aadhaar card
    if "aadhaar" in title_lower:
        remediated = re.sub(r"\b\d{4}[- ]?\d{4}[- ]?\d{4}\b", "[REDACTED_AADHAAR_NUMBER]", excerpt)
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Aadhaar numbers expose users to identity theft; masked per data-protection standards.",
            "estimated_fine_min": 20000.0,
            "estimated_fine_max": 100000.0,
            "affected_users_estimate": 1,
            "operational_impact": "Medium — identity-theft exposure.",
            "reputation_risk_level": "High"
        }

    # 14. SSN
    if "ssn" in title_lower:
        remediated = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[REDACTED_SSN]", excerpt)
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Plaintext SSNs are high-risk PII; secured via redaction.",
            "estimated_fine_min": 50000.0,
            "estimated_fine_max": 300000.0,
            "affected_users_estimate": 1,
            "operational_impact": "High — financial-fraud exposure.",
            "reputation_risk_level": "Critical"
        }

    # 15. SOX — bypass of internal financial controls
    if "bypass of internal financial controls" in title_lower:
        remediated = re.sub(
            r"\b(bypass|override|omit)\s+(internal\s+financial\s+controls|financial\s+sign-off|dual\s+control|ledger\s+verification)\b",
            r"enforce \2 with documented dual-control approval",
            excerpt, flags=re.I,
        )
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Bypassing internal financial controls violates SOX Section 404; dual-control approval reinstated.",
            "estimated_fine_min": 100000.0,
            "estimated_fine_max": 1000000.0,
            "affected_users_estimate": 0,
            "operational_impact": "Critical — statutory financial-control violation.",
            "reputation_risk_level": "Critical"
        }

    # 16. SOX — improper financial record destruction
    if "improper financial record destruction" in title_lower:
        remediated = re.sub(
            r"\b(delete|destroy|discard)\s+(financial\s+records|audit\s+workpapers|general\s+ledger|accounting\s+ledgers)\b",
            r"retain \2 for a minimum of 7 years under immutable storage",
            excerpt, flags=re.I,
        )
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "SOX Section 802 mandates 7-year retention of financial records; deletion instruction replaced with a retention policy.",
            "estimated_fine_min": 100000.0,
            "estimated_fine_max": 1000000.0,
            "affected_users_estimate": 0,
            "operational_impact": "Critical — statutory record-retention violation.",
            "reputation_risk_level": "Critical"
        }

    # 17. SOX — separation of duties deviation
    if "separation of duties deviation" in title_lower:
        remediated = re.sub(
            r"\b(single\s+signature|sole\s+approval|unilateral\s+signing)\b",
            "multi-party approval",
            excerpt, flags=re.I,
        )
        return {
            "remediated_text": remediated,
            "remediation_reasoning": "Unilateral approval above threshold violates SOX separation-of-duties controls; multi-party approval required.",
            "estimated_fine_min": 25000.0,
            "estimated_fine_max": 150000.0,
            "affected_users_estimate": 0,
            "operational_impact": "High — internal-control deviation.",
            "reputation_risk_level": "High"
        }

    # Fallback for unrecognized/custom-policy titles: use excerpt content as
    # a best-effort signal, since no title mapping exists for these.
    if "email" in text_lower or "@" in text_lower:
        return {
            "remediated_text": _redact_emails(excerpt),
            "remediation_reasoning": "Plain-text email is PII; masked to comply with GDPR Art. 5 (Data Minimisation).",
            "estimated_fine_min": 25000.0, "estimated_fine_max": 95000.0,
            "affected_users_estimate": 150,
            "operational_impact": "Medium — breach-notification duty under GDPR Art. 33 if leaked.",
            "reputation_risk_level": "High"
        }

    return {
        "remediated_text": "[REDACTED] " + excerpt,
        "remediation_reasoning": "General policy gap; redacted and access-restricted per standard guidelines.",
        "estimated_fine_min": 10000.0,
        "estimated_fine_max": 30000.0,
        "affected_users_estimate": 10,
        "operational_impact": "Low — minor governance discrepancy.",
        "reputation_risk_level": "Low"
    }


def _final_statement_from_report(report: str) -> str:
    """
    Extract a short, properly-written, complete finding from an agent's raw
    analysis text. Agents are prompted to return JSON (a "violations" list),
    so this parses that JSON first and renders it as plain English — the UI
    (Audit Desk chain-of-thought trace and agent council verdicts) must never
    display raw JSON. Falls back to the old free-text cleanup for any
    response that isn't valid JSON (e.g. an error stub).
    """

    if not report or not report.strip():
        return "No specific concerns were identified by this agent."

    report_str = report.strip()

    def _sentences_from_violations(violations: list) -> str:
        if not violations:
            return "No specific concerns were identified by this agent."
        parts = []
        for v in violations[:3]:
            if not isinstance(v, dict):
                continue
            title = (v.get("title") or "").strip()
            expl = (v.get("explanation") or "").strip()
            sev = (v.get("severity") or "").strip()
            sev_tag = f" ({sev})" if sev else ""
            if title and expl:
                parts.append(f"{title}{sev_tag}: {expl}")
            elif title:
                parts.append(f"{title}{sev_tag}.")
            elif expl:
                parts.append(expl)
        if not parts:
            return "No specific concerns were identified by this agent."
        text = " ".join(parts)
        remaining = len(violations) - min(len(violations), 3)
        if remaining > 0:
            text += f" ({remaining} additional finding{'s' if remaining != 1 else ''} omitted for brevity.)"
        return text

    # Preferred path: strict JSON parsing
    try:
        body = re.sub(r"^```(?:json)?\s*|\s*```$", "", report_str)
        payload = json.loads(body)
        if isinstance(payload, dict) and "violations" in payload:
            return _sentences_from_violations(payload.get("violations") or [])
    except Exception:
        pass

    # Fallback 1: Truncated/partial JSON regex extraction
    if "{" in report_str or "violations" in report_str:
        titles = re.findall(r'"title"\s*:\s*"([^"]+)"', report_str)
        severities = re.findall(r'"severity"\s*:\s*"([^"]+)"', report_str)
        explanations = re.findall(r'"explanation"\s*:\s*"([^"]+)"', report_str)

        parts = []
        for i in range(max(len(titles), len(explanations))):
            t = titles[i] if i < len(titles) else ""
            s = f" ({severities[i]})" if i < len(severities) else ""
            e = explanations[i] if i < len(explanations) else ""
            if t and e:
                parts.append(f"{t}{s}: {e}")
            elif t:
                parts.append(f"{t}{s}.")
            elif e:
                parts.append(e)

        if parts:
            return " ".join(parts[:3])

    # Fallback 2: Legacy free-text / non-JSON cleanup
    body = re.sub(r"^===.*REPORT ===\s*", "", report_str)
    body = re.sub(r'[{}"\[\]]', " ", body)
    body = re.sub(r"(?im)^\s*\d+\.\s*(violations?|severity|explanation|recommendations?)\s*:?\s*", "", body)
    body = re.sub(r"\s+", " ", body).strip()

    if not body:
        return "No specific concerns were identified by this agent."

    sentences = re.split(r"(?<=[.!?])\s+", body)
    final = ""
    for s in sentences:
        candidate = (final + " " + s).strip() if final else s
        if len(candidate) > 320 and final:
            break
        final = candidate
        if len(final) > 320:
            break

    if not final.endswith((".", "!", "?")):
        final = final.rstrip(",;: ") + "."

    return final


async def run_agent(agent_name: str, agent_prompt: str, text: str, vector_context: str) -> str:
    try:
        print(f"[DEBUG] Running {agent_name}")

        model = config.TRIAGE_MODEL
        print(f"[DEBUG] Using model: {model}")

        llm = _get_llm_client(
            model=model,
            temperature=0,
            max_tokens=700
        )

        prompt = f"""
            You are the {agent_name}.

            {agent_prompt}

            Analyze the following document.

            DOCUMENT:
            {_analysis_window(text)}

            REFERENCE:
            {vector_context}

            Return ONLY valid JSON.

            {{
                "agent": "{agent_name}",
                "violations": [
                    {{
                        "title": "",
                        "severity": "P2",
                        "source_regulation": "gdpr",
                        "excerpt": "",
                        "explanation": "",
                        "recommendation": ""
                    }}
                ]
            }}

            Rules:

            - Return ONLY valid JSON.
            - No markdown.
            - No explanation.
            - No prose.
            - No code block.
            - Do not invent violations.
            - If there are no violations, return:

            {{
                "agent": "{agent_name}",
                "violations": []
            }}
            """

        res = await _call_llm_with_retry(llm, prompt)

        print(f"[DEBUG] {agent_name} completed")

        return res.content

    except Exception as e:
        print(f"[{agent_name}] Failed: {e}")
        return f"=== {agent_name} REPORT ===\nFailed to execute analysis.\n"

def offline_compliance_audit(text: str):
    text_lower = text.lower()

    violations = []

    # Missing consent
    if "customer" in text_lower and "consent" not in text_lower:
        violations.append({"title": "Missing Consent Mechanism", "severity": "P2"})

    # Missing encryption
    if "customer" in text_lower and "encrypt" not in text_lower:
        violations.append({"title": "Encryption Controls Not Defined", "severity": "P2"})

    # Missing retention
    if "customer" in text_lower and "retention" not in text_lower:
        violations.append({"title": "Retention Policy Missing", "severity": "P2"})

    # Missing incident response
    if "incident" not in text_lower:
        violations.append({"title": "Incident Response Process Missing", "severity": "P3"})

    # Third-party processors
    if "third-party" in text_lower or "processor" in text_lower:
        violations.append({"title": "Third Party Processor Risk", "severity": "P2"})

    # Use the central scoring engine — no duplicate formula here.
    # Build lightweight Violation-like objects so calculate_compliance_score
    # can count severity levels.
    class _V:
        def __init__(self, sev): self.severity = type("S", (), {"value": sev})()
    v_objs = [_V(v["severity"]) for v in violations]
    score_result = calculate_compliance_score(v_objs, 0.0, 0, 1.0)

    return {
        "score": score_result["score"],
        "summary": f"Offline compliance agent identified {len(violations)} policy concerns.",
        "violations": violations
    }

def determine_severity(title, explanation):

    text = (title + " " + explanation).lower()

    critical = [
        "password",
        "credential",
        "secret",
        "api key",
        "token",
        "jwt",
        "bearer",
        "private key",
        "secret key"
    ]

    high = [
        "email",
        "phone",
        "salary",
        "credit card",
        "bank",
        "passport",
        "medical",
        "retention",
        "transfer",
        "unencrypted",
        "http",
        "pii"
    ]

    medium = [
        "classification",
        "policy",
        "label",
        "governance",
        "audit"
    ]

    if any(x in text for x in critical):
        return Severity.P1

    if any(x in text for x in high):
        return Severity.P2

    if any(x in text for x in medium):
        return Severity.P3

    return Severity.P4

def normalize_risk(title):

    t = title.lower()

    if "password" in t:
        return 100000,500000,100

    if "api key" in t:
        return 250000,1000000,500

    if "email" in t:
        return 25000,100000,150

    if "phone" in t:
        return 15000,50000,80

    if "salary" in t:
        return 10000,40000,1

    if "retention" in t:
        return 45000,180000,1250

    if "transfer" in t:
        return 150000,750000,2500

    if "classification" in t:
        return 5000,15000,0

    return 10000,30000,10

def normalize_title(title):

    t = title.lower()

    if any(x in t for x in [
        "password",
        "credential",
        "secret",
        "token",
        "jwt"
    ]):
        return "Hardcoded Credential"

    if "api" in t and "key" in t:
        return "Hardcoded API Key"

    if "email" in t:
        return "Email Exposure"

    if "phone" in t:
        return "Phone Number Exposure"

    if any(x in t for x in [
        "salary",
        "compensation"
    ]):
        return "Salary Disclosure"

    if "retention" in t:
        return "Retention Policy Violation"

    if any(x in t for x in [
        "classification",
        "label"
    ]):
        return "Missing Classification Label"

    if "transfer" in t:
        return "Cross Border Data Transfer"

    if "http" in t or "unencrypted" in t:
        return "Unencrypted Communication"

    if "access" in t:
        return "Excessive Access Permission"

    return title.strip()


async def _generate_ai_remediation(
    excerpt: str,
    source_regulation: str,
    recommendation: str,
    title: str,
    tenant_id: str,
    store,
) -> Dict[str, Any]:
    """
    Generate a real, non-empty compliant rewrite for a single violation.

    Reuses the existing ChromaDB-backed VectorStore (via `store.retrieve`)
    to ground the rewrite in the most relevant regulatory text, and reuses
    the existing `_get_llm_client` wrapper (no new LLM client, no new
    vector database) to produce the final rewrite text.

    Falls back to the deterministic `_suggest_remediation` regex engine if
    the LLM call fails or returns something unusable, so a placeholder or
    empty string is never persisted onto the Violation.
    """
    excerpt = (excerpt or "").strip()
    fallback = _suggest_remediation(title or "", excerpt)

    if not excerpt:
        return fallback

    try:
        query = f"{title}. {recommendation}"
        cites = store.retrieve(query, tenant_id=tenant_id, n=2)
        if cites:
            retrieved_context = "\n".join(
                f"- [{c.regulation.value}] {c.clause}: {c.text}" for c in cites
            )
        else:
            retrieved_context = "- No additional regulatory context retrieved."

        prompt = f"""
You are the Autonomous Remediation Agent. Rewrite the clause below so it is
fully compliant, preserving as much of the original intent, tone and
surrounding wording as possible.

VIOLATED REGULATION: {source_regulation}

ORIGINAL CLAUSE:
{excerpt}

REMEDIATION RECOMMENDATION:
{recommendation or "Bring the clause into compliance."}

RETRIEVED REGULATORY CONTEXT:
{retrieved_context}

Return ONLY the rewritten clause text — no preamble, no explanation, no
markdown, no quotation marks. It must be a drop-in replacement for the
original clause and must never be empty.
"""
        llm = _get_llm_client(model=config.ANALYSIS_MODEL, temperature=0.1, max_tokens=400)
        response = await _call_llm_with_retry(llm, prompt)
        rewrite = (response.content or "").strip()
        rewrite = rewrite.strip('"').strip("'").strip()
        # Strip accidental markdown fences
        rewrite = re.sub(r"^```(?:\w+)?\s*", "", rewrite)
        rewrite = re.sub(r"\s*```$", "", rewrite).strip()

        if rewrite and rewrite.lower() != excerpt.lower():
            fallback["remediated_text"] = rewrite
            fallback["remediation_reasoning"] = (
                f"AI-generated compliant rewrite grounded in {source_regulation.upper()} "
                "and retrieved policy context."
            )
        return fallback

    except Exception as e:
        print(f"[agents] AI remediation generation failed ({e}); using deterministic rewrite.")
        return fallback


# ─── MULTI-AGENT COUNCIL FUNCTION ─────────────────────────────────────────────
async def run_multi_agent_council(
    filename: str,
    text: str,
    uploaded_by: str,
    department: str,
    tenant_id: str = config.DEFAULT_TENANT
) -> ScanRecord:
    """Runs the collaborative multi-agent council scanning pipeline with async parallel agents."""
    
    # 1. Run deterministic checks first to bootstrap findings (and fallback vector citations)
    rule_findings = run_rules(text)
    store = get_store()
    
    # Ground rule findings in citations
    grounded_findings: List[Violation] = []
    for f in rule_findings:
        query = f"{f.title}. {f.explanation}"
        cites = store.retrieve(query, tenant_id=tenant_id, n=1)
        if cites and cites[0].similarity >= store.min_similarity:
            f.citation = cites[0]
        # Populate the AI-compliant rewrite fields immediately so every
        # downstream path (triage bypass, LLM-merge, or offline fallback)
        # carries a real remediated_text instead of leaving it blank —
        # run_rules() itself never sets these fields.
        if not f.remediated_text:
            rem_details = _suggest_remediation(f.title, f.excerpt)
            f.remediation_reasoning = rem_details["remediation_reasoning"]
            f.remediated_text = rem_details["remediated_text"]
            f.estimated_fine_min = rem_details["estimated_fine_min"]
            f.estimated_fine_max = rem_details["estimated_fine_max"]
            f.affected_users_estimate = rem_details["affected_users_estimate"]
            f.operational_impact = rem_details["operational_impact"]
            f.reputation_risk_level = rem_details["reputation_risk_level"]
        grounded_findings.append(f)
        
    violations: List[Violation] = []
    summary_text = ""
    llm_success = False
    ai_compliance_score = None
    confidence = 0.75  # Default confidence for deterministic or fallback analyses
    agent_verdicts: List[dict] = []  # per-agent stance for the council view
    
    # ─── LIVE LLM PATH ────────────────────────────────────────────────────────
    if not config.DEMO_MODE:
        try:
            # Retrieve global vector store context and format RAG citations
            context_chunks = store.retrieve(text[:2500], tenant_id=tenant_id, n=3)
            if context_chunks:
                vector_context = "\n".join(
                    f"- [{c.regulation.value}] {c.clause}: {c.text}" for c in context_chunks
                )
            else:
                vector_context = "- No policy citations were available for this tenant."

            # --- Tier 1: Triage Check (from analyzer.py strategy) ---
            triage_llm = _get_llm_client(model=config.TRIAGE_MODEL, temperature=0)
            triage_prompt = f"""
                You are a compliance triage classifier.

                Determine whether this document requires compliance analysis.

                Return EXACTLY one word.

                YES

                or

                NO

                A document requires analysis if it contains any of:

                - personal data
                - employee data
                - customer data
                - passwords
                - credentials
                - API keys
                - tokens
                - secrets
                - financial data
                - salary
                - contracts
                - GDPR
                - ISO 27001
                - SOX
                - policies
                - retention
                - encryption
                - security controls

                No explanation.

                No punctuation.

                DOCUMENT

                {_analysis_window(text)}
            """
            try:
                triage_res = await _call_llm_with_retry(triage_llm, triage_prompt)
                print("[DEBUG] TRIAGE CALLED")
                print("[DEBUG] TRIAGE RESPONSE:", triage_res.content)
                is_relevant = "yes" in triage_res.content.lower()
            except Exception as e:
                # A rate-limited/failed triage call must NOT sink the entire
                # agentic run — that was silently dropping us into the fully
                # deterministic fallback path even though the real agent
                # council below was perfectly capable of running. Default to
                # "relevant" (the safer assumption for a compliance scan) and
                # proceed to the actual LLM agent council.
                print(f"[agents] Triage call failed ({e}); assuming relevant and "
                      f"proceeding to full agent council instead of bailing out.")
                is_relevant = True
            
            if not is_relevant:
                # Bypass deep analysis if document is not compliance-relevant
                violations = grounded_findings
                crit = sum(1 for v in violations if v.severity == Severity.P1)
                high = sum(1 for v in violations if v.severity == Severity.P2)
                if not violations:
                    summary_text = "Compliance Council review: no violations found. Document is fully compliant."
                else:
                    summary_text = (
                        f"Compliance Council review: {len(violations)} issue(s) found "
                        f"({crit} Critical, {high} High). Remediation recommended."
                    )
                confidence = 0.85
                llm_success = True
            else:
                # --- Tier 2: Sequential Agent Execution ---

                agent_configs = [
                    ("GDPR Agent", GDPR_AGENT_PROMPT),
                    ("Security Agent", SECURITY_AGENT_PROMPT),
                    ("Legal Agent", LEGAL_AGENT_PROMPT),
                    ("Internal Policy Agent", POLICY_AGENT_PROMPT),
                ]

                reports = []

                print("[DEBUG] STARTING AGENT COUNCIL")

                for agent_name, agent_prompt in agent_configs:
                    try:
                        report = await run_agent(
                            agent_name,
                            agent_prompt,
                            text,
                            vector_context
                        )

                        reports.append(report)

                        # Capture a structured stance for the council view
                        rl = report.lower()
                        flagged = any(k in rl for k in (
                            "non-compliant", "violation", "risk", "exposure",
                            "breach", "missing", "unencrypted", "flag"
                        )) and "no violation" not in rl and "fully compliant" not in rl
                        snippet = _final_statement_from_report(report)
                        agent_verdicts.append({
                            "agent": agent_name,
                            "verdict": "Concern raised" if flagged else "No concern",
                            "rationale": snippet,
                        })

                        # small delay prevents TPM/RPM spikes against the LLM
                        # provider's per-minute limits (tune with
                        # AGENT_STEP_DELAY_SECONDS if you're still seeing 429s)
                        await asyncio.sleep(_AGENT_STEP_DELAY_SECONDS)

                    except Exception as e:
                        print(f"[{agent_name}] Failed: {e}")

                        reports.append(
                            f"=== {agent_name} REPORT ===\nFailed to execute analysis.\n"
                        )
                        agent_verdicts.append({
                            "agent": agent_name,
                            "verdict": "Unavailable",
                            "rationale": "Agent could not complete its analysis.",
                        })

                print("[DEBUG] AGENT COUNCIL FINISHED")

                combined_reports = "\n".join(reports)
                
                # --- Tier 3: Consensus Council Step ---
                if config.GROQ_API_KEY:
                    llm_consensus = _get_llm_client(
                        model=config.ANALYSIS_MODEL,
                        temperature=0,
                        max_tokens=4096,
                        structured_output=False
                    )
                    llm_consensus.model_kwargs = {"response_format": {"type": "json_object"}}
                else:
                    llm_consensus = _get_llm_client(
                        model=config.ANALYSIS_MODEL,
                        temperature=0,
                        max_tokens=4096,
                        structured_output=True
                    )
                
                consensus_prompt = f"""
                    You are the Enterprise Compliance Council.

                    The individual agents have ALREADY analyzed the document.

                    Your job is ONLY to consolidate their findings.

                    ==========================
                    STRICT RULES
                    ==========================

                    1. NEVER invent a new violation.
                    2. NEVER remove a violation unless two findings describe the EXACT same issue.
                    3. Preserve the severity assigned by the reporting agent whenever available.
                    4. If no severity exists, choose the most conservative reasonable severity.
                    5. NEVER change the excerpt.
                    6. NEVER estimate financial penalties.
                    7. NEVER estimate affected users.
                    8. NEVER estimate compliance score.
                    9. NEVER invent regulations.
                    10. NEVER rewrite recommendations.
                    11. Keep "summary", "explanation" and "remediation_reasoning" concise and
                        professional (1-2 sentences each). Preserve the specific regulation/rule
                        citation and the concrete evidence (e.g. the offending data/clause), but
                        remove filler, hedging, and repeated context.
                    12. Return ONLY valid JSON.
                    13. No markdown.
                    14. No explanation outside the JSON.

                    ==========================
                    AGENT REPORTS
                    ==========================

                    {combined_reports}

                    ==========================
                    OUTPUT
                    ==========================

                    Return EXACTLY ONE JSON OBJECT.

                    {{
                        "summary": "Executive summary",
                        "confidence": 0.95,
                        "violations": [
                            {{
                                "title": "",
                                "severity": "P1",
                                "source_regulation": "gdpr",
                                "detected_by": "GDPR Agent",
                                "excerpt": "",
                                "explanation": "",
                                "recommendation": "",
                                "remediation_reasoning": "",
                                "remediated_text": "",
                                "operational_impact": "",
                                "reputation_risk_level": "High"
                            }}
                        ]
                    }}

                    Return ONLY JSON.
                    """
                
                # Invoke consensus
                if config.GROQ_API_KEY:
                    llm_success = False
                    confidence = 0.75
                    try:
                        response = (await _call_llm_with_retry(llm_consensus, consensus_prompt)).content
                    except Exception as consensus_err:
                        # The 4 per-agent LLM calls above already succeeded —
                        # a rate-limited/failed *consensus* call shouldn't
                        # throw all of that away and drop us into the fully
                        # deterministic/offline path. Build the result
                        # directly from the agent verdicts we already have.
                        print(f"[agents] Consensus call failed ({consensus_err}); "
                              f"using per-agent council results directly instead "
                              f"of the deterministic fallback.")
                        violations = grounded_findings
                        crit = sum(1 for v in violations if v.severity == Severity.P1)
                        high = sum(1 for v in violations if v.severity == Severity.P2)
                        concerns = sum(1 for v in agent_verdicts if v["verdict"] == "Concern raised")
                        summary_text = (
                            f"Compliance Council review (per-agent, consensus step unavailable): "
                            f"{concerns} of {len(agent_verdicts)} agents raised concerns. "
                            f"{len(violations)} rule-based issue(s) also found "
                            f"({crit} Critical, {high} High)."
                        )
                        confidence = 0.7
                        llm_success = True
                        raise _ConsensusHandled()
                    clean_resp = re.sub(r"^```json\s*", "", response.strip())
                    clean_resp = re.sub(r"\s*```$", "", clean_resp)
                    print("\n========== CONSENSUS RESPONSE ==========")
                    print(clean_resp[:5000])
                    print("\n========== END RESPONSE ==========")
                    print("Response length:", len(clean_resp))
                    try:
                        consensus_data = json.loads(clean_resp)
                        print(consensus_data.keys())
                        ai_compliance_score = consensus_data.get(
                            "compliance_score"
                        )

                        risk_level = consensus_data.get(
                            "risk_level",
                            "Medium"
)

                    except Exception as parse_error:

                        print("\nJSON PARSE FAILED")
                        print(parse_error)

                        print("\nRAW RESPONSE:")
                        print(clean_resp)

                        raise
                else:
                    consensus_data = await _call_llm_with_retry(llm_consensus, consensus_prompt)
                    if hasattr(consensus_data, "model_dump"):
                        consensus_data = consensus_data.model_dump()
                        
                summary_text = consensus_data.get("summary", "Analysis finished.")
                confidence = consensus_data.get("confidence", 0.9)
                if confidence < 0.60:
                    print("[CONSENSUS] Confidence too low. Falling back.")
                    raise ValueError("Low confidence")
                
                raw_violations = consensus_data.get("violations", [])
                for idx, r_v in enumerate(raw_violations):
                    sev_val = r_v.get("severity", "P3")
                    if sev_val not in [s.value for s in Severity]:
                        sev_val = "P3"
                        
                    reg_val = r_v.get("source_regulation", "gdpr")
                    if reg_val not in [r.value for r in Regulation]:
                        reg_val = "gdpr"

                    violation_key = (
                        r_v.get("title", "")
                        + r_v.get("excerpt", "")
                        + r_v.get("source_regulation", "")
                    )
                    fine_min,fine_max,users = normalize_risk(
                                                r_v.get("title","")
                                            )
                    llm_excerpt = r_v.get("excerpt", "Exceeding clause limits")
                    from app.pipeline.doc_remediator import find_source_span
                    snapped = find_source_span(text, llm_excerpt)
                    violation = Violation(
                        id="v_" + hashlib.md5(violation_key.encode()).hexdigest()[:10],
                        title = normalize_title(
                            r_v.get("title","Compliance Violation")
                        ),
                        severity=determine_severity(
                            r_v.get("title",""),
                            r_v.get("explanation","")
                        ),
                        source_regulation=Regulation(reg_val),
                        detected_by=r_v.get("detected_by", "Compliance Council"),
                        # Prefer the exact verbatim span found in the actual
                        # document text over whatever the LLM reported, so
                        # the document-regeneration replacement step later
                        # is guaranteed to find real text to swap out — a
                        # paraphrased/reworded LLM excerpt would otherwise
                        # silently fail to match and leave the original
                        # violating clause in the downloaded document even
                        # though the score reports it as resolved.
                        excerpt=snapped or llm_excerpt,
                        explanation=r_v.get("explanation", "Potential risk identified."),
                        recommendation=r_v.get("recommendation", "Review and replace."),
                        remediation_reasoning=r_v.get("remediation_reasoning"),
                        remediated_text=r_v.get("remediated_text"),
                        remediation_score_improvement=5 if sev_val == "P4" else 10 if sev_val == "P3" else 15 if sev_val == "P2" else 22,
                        risk_multiplier=1.0,
                        estimated_fine_min=fine_min,
                        estimated_fine_max=fine_max,
                        affected_users_estimate=users,
                        operational_impact=r_v.get("operational_impact", ""),
                        reputation_risk_level=r_v.get("reputation_risk_level", "Medium")
                    )
                    
                    cite_query = f"{violation.title}. {violation.explanation}"
                    cites = store.retrieve(cite_query, tenant_id=tenant_id, n=1)
                    if cites and cites[0].similarity >= store.min_similarity:
                        violation.citation = cites[0]

                    # The consensus LLM only consolidates agent reports and
                    # is not reliable about emitting a usable rewrite, so
                    # remediated_text can arrive empty here. Never let an
                    # empty/placeholder rewrite reach the ScanRecord: use
                    # the existing ChromaDB retrieval + LLM wrapper to
                    # generate a real compliant rewrite for this violation.
                    if not (violation.remediated_text or "").strip():
                        rem_details = await _generate_ai_remediation(
                            excerpt=violation.excerpt,
                            source_regulation=violation.source_regulation.value,
                            recommendation=violation.recommendation,
                            title=violation.title,
                            tenant_id=tenant_id,
                            store=store,
                        )
                        violation.remediated_text = rem_details["remediated_text"]
                        if not (violation.remediation_reasoning or "").strip():
                            violation.remediation_reasoning = rem_details["remediation_reasoning"]

                    violations.append(violation)
                
                # Merge rule violations
                merged = {}

                for v in grounded_findings:

                    key = (
                        v.title.lower().strip(),
                        v.source_regulation.value
                    )

                    merged[key] = v

                for v in violations:

                    key = (
                        v.title.lower().strip(),
                        v.source_regulation.value
                    )

                    if key not in merged:
                        merged[key] = v

                violations = list(merged.values())
                llm_success = True
                
        except _ConsensusHandled:
            # violations/summary_text/confidence/llm_success were already set
            # to a valid per-agent-council result right before this was
            # raised — nothing further to do here.
            pass
        except Exception as e:
            print(f"[agents] Real LLM path failed: {e}. Falling back to dynamic simulation mode.")
            violations = []
            summary_text = ""
            confidence = 0.6
            
    # ─── DEMO DYNAMIC SIMULATION PATH ──────────────────────────────────────────
    if not llm_success:
        offline_result = offline_compliance_audit(text)

        summary_text += (
            "\n\n" +
            offline_result["summary"]
        )

        if grounded_findings:
            confidence = min(
                0.95,
                0.70 + (len(grounded_findings) * 0.04)
            )
        else:
            confidence = 0.90
        # We enrich the grounded rule-engine violations with simulator metrics and remediations
        for v in grounded_findings:
            # Generate remediation fields
            rem_details = _suggest_remediation(v.title, v.excerpt)
            
            # Dynamic regulation mapping based on filename to ensure all filters have data
            source_reg = v.source_regulation
            fn_lower = filename.lower()
            if "sox" in fn_lower or "financial" in fn_lower:
                source_reg = Regulation.SOX
            elif "iso27001" in fn_lower:
                source_reg = Regulation.ISO27001
            
            # Map detecting agents dynamically
            agents_list = ["Legal Agent"]
            if source_reg == Regulation.GDPR:
                agents_list.append("GDPR Agent")
            elif source_reg == Regulation.INTERNAL_SECURITY or source_reg == Regulation.ISO27001:
                agents_list.append("Security Agent")
            elif source_reg == Regulation.INTERNAL_HR:
                agents_list.append("Internal Policy Agent")
            else:
                agents_list.append("Internal Policy Agent")
                
            # Compute score improvement based on tier
            score_imp = 22 if v.severity == Severity.P1 else 12 if v.severity == Severity.P2 else 5 if v.severity == Severity.P3 else 2
            
            # Construct Violation
            enriched_v = Violation(
                id=v.id,
                title=v.title,
                severity=v.severity,
                source_regulation=source_reg,
                detected_by=" + ".join(sorted(agents_list)),
                excerpt=v.excerpt,
                explanation=v.explanation,
                recommendation=v.recommendation,
                citation=v.citation,
                remediation_reasoning=rem_details["remediation_reasoning"],
                remediated_text=rem_details["remediated_text"],
                remediation_score_improvement=score_imp,
                risk_multiplier=1.0,
                estimated_fine_min=rem_details["estimated_fine_min"],
                estimated_fine_max=rem_details["estimated_fine_max"],
                affected_users_estimate=rem_details["affected_users_estimate"],
                operational_impact=rem_details["operational_impact"],
                reputation_risk_level=rem_details["reputation_risk_level"]
            )
            violations.append(enriched_v)
            
        # Compile summary text dynamically
        crit = sum(1 for v in violations if v.severity == Severity.P1)
        high = sum(1 for v in violations if v.severity == Severity.P2)
        med = sum(1 for v in violations if v.severity == Severity.P3)
        
        if not violations:
            summary_text = "Compliance Council review: no violations found. Document is fully compliant."
        else:
            summary_text = (
                f"Compliance Council review: {len(violations)} issue(s) found "
                f"({crit} Critical, {high} High). Remediation recommended."
            )

    # ─── AGGREGATE RISK CALCULATIONS ──────────────────────────────────────────
    total_exposure_min = sum(v.estimated_fine_min for v in violations)
    total_exposure_max = sum(v.estimated_fine_max for v in violations)
    total_affected_users = sum(v.affected_users_estimate for v in violations)
    

    # =====================================================
    # ENTERPRISE COMPLIANCE SCORE ENGINE
    # =====================================================
    score_result = calculate_compliance_score(violations, total_exposure_max, total_affected_users, confidence)
    compliance_score = score_result["score"]

    # ScanRecord.score_breakdown expects a List[dict] of line items
    # (e.g. [{"factor": ..., "detail": ..., "points": ...}, ...]), but
    # calculate_compliance_score returns a single flat dict of penalties.
    # Convert it here so the shape always matches the model.
    _penalty_labels = {
        "critical_penalty": "Critical violations",
        "high_penalty": "High violations",
        "medium_penalty": "Medium violations",
        "low_penalty": "Low violations",
        "exposure_penalty": "Financial exposure",
        "affected_users_penalty": "Affected users",
        "confidence_penalty": "Low analysis confidence",
    }
    score_breakdown = [
        {"factor": _penalty_labels.get(key, key), "detail": key, "points": points}
        for key, points in score_result["breakdown"].items()
        if points
    ]
    risk_points = score_result["risk_points"]
    critical = score_result["critical"]
    high = score_result["high"]
    medium = score_result["medium"]
    low = score_result["low"]

    # Calculate severity breakdown
    breakdown = {s.value: 0 for s in Severity}
    for v in violations:
        breakdown[v.severity.value] += 1

    # ─── MAP EACH FINDING TO SPECIFIC STATUTORY CLAUSES ───────────────────────
    for v in violations:
        if not v.regulation_articles:
            v.regulation_articles = map_articles(
                v.title, v.source_regulation.value, v.explanation
            )

    # ─── RESOLVE CONFLICTS & PRECEDENCE ───────────────────────────────────────
    violations = resolve_conflicts(violations)

    # Honest analysis-mode label (no silent masking of the fallback path)
    if config.DEMO_MODE:
        analysis_mode = "demo"
    elif llm_success:
        analysis_mode = "agentic_llm"
    else:
        analysis_mode = "deterministic_fallback"

    print("\n===================")
    print("FINAL SCORE:", compliance_score, "| MODE:", analysis_mode)
    print("===================\n")

    return ScanRecord(
        scan_id=f"scan_{uuid.uuid4().hex[:10]}",
        document_name=filename,
        uploaded_by=uploaded_by,
        department=department,
        tenant_id=tenant_id,
        created_at=datetime.now(timezone.utc),
        compliance_score=compliance_score,
        compliance_status=score_result["status"],
        risk_level=score_result["risk_level"],
        total_violations=len(violations),
        severity_breakdown=breakdown,
        violations=violations,
        summary=summary_text,
        demo_mode=config.DEMO_MODE,
        confidence=confidence,
        total_exposure_min=total_exposure_min,
        total_exposure_max=total_exposure_max,
        total_affected_users=total_affected_users,
        raw_text=text,
        score_breakdown=score_breakdown,
        analysis_mode=analysis_mode,
        agent_reports=agent_verdicts,
    )