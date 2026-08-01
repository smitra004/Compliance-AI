"""
Deterministic regulation-to-article mapping.

Every finding is mapped to the specific statutory clauses it implicates.
This is intentionally rule-based (not LLM-generated) so the mapping is
auditable and defensible: a reviewer can trace exactly why a given
violation cites a given article. Rule-engine findings map by their fixed
title; LLM-surfaced findings fall back to a regulation + keyword map.
"""
from __future__ import annotations

from typing import List

# ── Exact mapping for deterministic rule-engine findings (by fixed title) ──
TITLE_ARTICLE_MAP = {
    "Hard-coded credential / secret exposed": ["ISO 27001 A.8.24", "ISO 27001 A.5.15"],
    "Unprotected personal data (email addresses)": ["GDPR Art. 5(1)(f)", "GDPR Art. 32"],
    "Unprotected personal data (phone numbers)": ["GDPR Art. 5(1)(c)", "GDPR Art. 32"],
    "Compensation data in shared document": ["Internal HR-COMP-01", "GDPR Art. 5(1)(c)"],
    "Excessive / indefinite data retention": ["GDPR Art. 5(1)(e)", "GDPR Art. 17"],
    "Cross-border transfer without safeguards": ["GDPR Art. 44", "GDPR Art. 46"],
    "Confidential data over unencrypted channel": ["GDPR Art. 32", "ISO 27001 A.8.24"],
    "Overly broad access granted": ["ISO 27001 A.5.15", "ISO 27001 A.8.2"],
    "Missing data classification label": ["ISO 27001 A.5.12"],
    "Informal tone in policy document": ["Internal DOC-STYLE-01"],
    "Exposed Credit Card Sensitive Data": ["PCI-DSS Req. 3.4", "GDPR Art. 32"],
    "Exposed PAN Card Personal Data": ["GDPR Art. 32", "IT Act 2000 §43A"],
    "Exposed Aadhaar Card Personal Data": ["Aadhaar Act §29", "GDPR Art. 32"],
    "Exposed SSN Personal Data": ["GDPR Art. 32", "GLBA §501(b)"],
    "Bypass of Internal Financial Controls": ["SOX §404", "COSO Principle 10"],
    "Improper Financial Record Destruction": ["SOX §802", "ISO 27001 A.5.33"],
    "Separation of Duties Deviation": ["SOX §404", "ISO 27001 A.5.3"],
    # Offline-audit titles
    "Missing Consent Mechanism": ["GDPR Art. 6", "GDPR Art. 7"],
    "Encryption Controls Not Defined": ["GDPR Art. 32", "ISO 27001 A.8.24"],
    "Retention Policy Missing": ["GDPR Art. 5(1)(e)", "GDPR Art. 17"],
    "Incident Response Process Missing": ["GDPR Art. 33", "ISO 27001 A.5.24"],
    "Third Party Processor Risk": ["GDPR Art. 28", "ISO 27001 A.5.19"],
}

# ── Keyword fallback for LLM-surfaced findings, scoped by regulation ──
# (regulation_value, keyword) -> articles. Checked in order; first hit wins.
KEYWORD_MAP = [
    ("gdpr", ("transfer", "cross-border", "offshore", "overseas"), ["GDPR Art. 44", "GDPR Art. 46"]),
    ("gdpr", ("retention", "erasure", "delete", "indefinite"), ["GDPR Art. 5(1)(e)", "GDPR Art. 17"]),
    ("gdpr", ("consent",), ["GDPR Art. 6", "GDPR Art. 7"]),
    ("gdpr", ("special category", "sensitive data", "art. 9", "health data", "biometric"), ["GDPR Art. 9"]),
    ("gdpr", ("breach", "notification"), ["GDPR Art. 33", "GDPR Art. 34"]),
    ("gdpr", ("encrypt", "unencrypted", "security", "plaintext", "plain text", "pii", "personal data"), ["GDPR Art. 32"]),
    ("sox", ("retention", "destruction", "destroy", "discard", "records"), ["SOX §802"]),
    ("sox", ("control", "bypass", "override", "sign-off", "duties", "approval"), ["SOX §404"]),
    ("iso27001", ("access", "privilege", "permission"), ["ISO 27001 A.5.15"]),
    ("iso27001", ("encrypt", "cryptograph", "key"), ["ISO 27001 A.8.24"]),
    ("iso27001", ("incident", "response"), ["ISO 27001 A.5.24"]),
    ("internal_security", ("access", "privilege", "least privilege"), ["ISO 27001 A.5.15"]),
    ("internal_security", ("encrypt", "unencrypted", "transit", "channel"), ["ISO 27001 A.8.24", "GDPR Art. 32"]),
    ("internal_security", ("incident", "response"), ["ISO 27001 A.5.24"]),
    ("internal_security", ("classification", "label"), ["ISO 27001 A.5.12"]),
]

# ── Last-resort default per regulation ──
REGULATION_DEFAULT = {
    "gdpr": ["GDPR Art. 5"],
    "sox": ["SOX §404"],
    "iso27001": ["ISO 27001 A.5.1"],
    "internal_security": ["ISO 27001 A.5.1"],
    "internal_hr": ["Internal HR Policy"],
    "custom": ["Internal Policy"],
}


def map_articles(title: str, regulation_value: str, explanation: str = "") -> List[str]:
    """Return the specific statutory clauses a finding implicates."""
    title = (title or "").strip()
    if title in TITLE_ARTICLE_MAP:
        return list(TITLE_ARTICLE_MAP[title])

    haystack = f"{title} {explanation}".lower()
    reg = (regulation_value or "").lower()
    for reg_key, keywords, articles in KEYWORD_MAP:
        if reg_key == reg and any(k in haystack for k in keywords):
            return list(articles)

    # cross-regulation keyword sweep (regulation field may be imprecise from LLM)
    for _reg_key, keywords, articles in KEYWORD_MAP:
        if any(k in haystack for k in keywords):
            return list(articles)

    return list(REGULATION_DEFAULT.get(reg, ["Internal Policy"]))
