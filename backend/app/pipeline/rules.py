"""Deterministic rule engine. Regex-based detectors each carry a fixed
severity tier (P1-P4) and a source regulation. This layer is fully
auditable and always runs, independent of any LLM."""
from __future__ import annotations

import re
import uuid
from typing import List

from app.models import Regulation, Severity, Violation


class Rule:
    def __init__(self, rid, title, pattern, severity, regulation,
                 explanation, recommendation, flags=re.IGNORECASE):
        self.rid = rid
        self.title = title
        self.pattern = re.compile(pattern, flags)
        self.severity = severity
        self.regulation = regulation
        self.explanation = explanation
        self.recommendation = recommendation


# Verhoeff algorithm tables for Aadhaar verification
VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

def validate_aadhaar(number_str: str) -> bool:
    cleaned = re.sub(r"[- ]", "", number_str)
    if not cleaned.isdigit() or len(cleaned) != 12:
        return False
    if cleaned[0] in ('0', '1'):
        return False
        
    c = 0
    for i, item in enumerate(reversed(cleaned)):
        digit = int(item)
        p_val = VERHOEFF_P[i % 8][digit]
        c = VERHOEFF_D[c][p_val]
    return c == 0

def validate_credit_card(number_str: str) -> bool:
    cleaned = re.sub(r"[- ]", "", number_str)
    if not cleaned.isdigit() or len(cleaned) < 13 or len(cleaned) > 19:
        return False
    total = 0
    reverse_digits = [int(d) for d in reversed(cleaned)]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


RULES: List[Rule] = [

    Rule(
        "R-CRED",
        "Hard-coded credential / secret exposed",
        # Excludes safe indirections (env-var lookups, vault refs, redaction
        # placeholders) so a remediated value doesn't re-trigger this rule.
        r"(api[_-]?key|secret|password|passwd|token|bearer)\s*[:=]\s*"
        r"(?!os\.getenv|os\.environ|process\.env|System\.getenv|getenv\(|"
        r"vault\.|secrets_manager|keyvault|\[REDACTED|<REDACTED|\*{3,})\S+",
        Severity.P1, Regulation.INTERNAL_SECURITY,
        "A credential or secret appears in plain text. Hard-coded secrets are a critical security violation and a common breach vector.",
        "Remove the secret from the document and rotate it. Store secrets in a vault or environment variables.",
    ),
    Rule(
        "R-PII-PHONE",
        "Unprotected personal data (phone numbers)",
        r"(?<!\d)(\+?\d{1,3}[\s-]?)?(\(?\d{3}\)?[\s-]?)\d{3}[\s-]?\d{4}(?!\d)",
        Severity.P2, Regulation.GDPR,
        "Phone numbers are personal data under GDPR and appear without protection controls.",
        "Mask or tokenise phone numbers in shared documents.",
    ),
    Rule(
        "R-RETENTION",
        "Excessive / indefinite data retention",
        r"(retain|retention|keep|store).{0,40}?(indefinit|forever|permanent|7\s*years|10\s*years|99\s*years)",
        Severity.P2, Regulation.GDPR,
        "An indefinite or excessive retention period conflicts with GDPR storage-limitation and the right to erasure (Art. 17).",
        "Define a finite retention period aligned to the processing purpose and the approved schedule.",
    ),
    Rule(
        "R-TRANSFER",
        "Cross-border transfer without safeguards",
        r"(transfer|send|share|upload).{0,40}?(us servers|united states|third country|offshore|overseas)",
        Severity.P1, Regulation.GDPR,
        "Personal data may be transferred outside the EU without documented safeguards, contrary to GDPR Art. 44.",
        "Use an adequacy mechanism or standard contractual clauses; prefer in-region processing.",
    ),
    Rule(
        "R-UNENCRYPTED",
        "Confidential data over unencrypted channel",
        r"(unencrypted|plain[\s-]?text|http://|cleartext).{0,40}?(email|link|share|send|transmit)",
        Severity.P2, Regulation.INTERNAL_SECURITY,
        "Confidential data is shared over an unencrypted channel, violating the encryption-in-transit policy.",
        "Share only over TLS/encrypted channels; never use plain HTTP for confidential data.",
    ),
    Rule(
        "R-ACCESS",
        "Overly broad access granted",
        r"(grant|give|allow).{0,30}?(everyone|all users|public|unrestricted|full access)",
        Severity.P2, Regulation.INTERNAL_SECURITY,
        "Broad or unrestricted access conflicts with the least-privilege access-control policy.",
        "Scope access to specific roles following least-privilege.",
    ),
    Rule(
        "R-CLASS",
        "Missing data classification label",
        r"^(?!.*\b(public|internal|confidential|restricted)\b).*$",
        Severity.P3, Regulation.INTERNAL_SECURITY,
        "The document carries no data-classification label (Public / Internal / Confidential / Restricted).",
        "Add a classification label in the document header.",
        flags=re.IGNORECASE | re.DOTALL,
    ),
    Rule(
        "R-INFORMAL",
        "Informal tone in policy document",
        r"\b(hey|thanks|please review|ping me)\b",
        Severity.P4, Regulation.INTERNAL_HR,
        "Policy documents should maintain a formal tone and avoid informal colloquialisms like 'hey' or 'ping me'.",
        "Consider replacing with formal corporate phrasing.",
      ),
    Rule(
        "R-PII-CREDITCARD",
        "Exposed Credit Card Sensitive Data",
        r"\b(?:\d[ -]*?){13,16}\b",
        Severity.P1, Regulation.GDPR,
        "A credit card number appears in the document. Sharing payment card details in plain text violates PCI-DSS and GDPR data security guidelines.",
        "Remove the credit card details immediately and use tokenised payments.",
    ),
    Rule(
        "R-PII-PAN",
        "Exposed PAN Card Personal Data",
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
        Severity.P1, Regulation.GDPR,
        "An Indian PAN card number was detected. PAN numbers represent critical PII and must be protected under national privacy frameworks.",
        "Redact or encrypt the PAN card number.",
    ),
    Rule(
        "R-PII-AADHAAR",
        "Exposed Aadhaar Card Personal Data",
        r"\b\d{4}[- ]?\d{4}[- ]?\d{4}\b",
        Severity.P1, Regulation.GDPR,
        "An Aadhaar card number was detected. Sharing Aadhaar numbers in plaintext exposes users to identity theft and violates data protection standards.",
        "Redact or mask the Aadhaar card number.",
    ),
    Rule(
        "R-PII-SSN",
        "Exposed SSN Personal Data",
        r"\b\d{3}-\d{2}-\d{4}\b",
        Severity.P1, Regulation.GDPR,
        "A Social Security Number (SSN) was detected. Plaintext SSNs are high-risk PII that could lead to financial fraud and regulatory fines under privacy laws.",
        "Remove or secure the SSN using cryptographic hashing.",
    ),
    Rule(
        "R-SOX-CONTROLS",
        "Bypass of Internal Financial Controls",
        r"\b(bypass|override|omit)\s+(internal\s+financial\s+controls|financial\s+sign-off|dual\s+control|ledger\s+verification)\b",
        Severity.P1, Regulation.SOX,
        "Bypassing or overriding internal financial controls is a critical compliance violation under SOX Section 404.",
        "Enforce dual-control approvals and log ledger adjustments in the financial system.",
    ),
    Rule(
        "R-SOX-RETENTION",
        "Improper Financial Record Destruction",
        r"\b(delete|destroy|discard)\s+(financial\s+records|audit\s+workpapers|general\s+ledger|accounting\s+ledgers)\b",
        Severity.P1, Regulation.SOX,
        "SOX Section 802 mandates the retention of audit and financial records for at least 7 years. Deleting them violates statutory requirements.",
        "Configure immutable storage policies to prevent premature deletion of accounting ledgers.",
    ),
    Rule(
        "R-SOX-AUTHORITY",
        "Separation of Duties Deviation",
        r"\b(single\s+signature|sole\s+approval|unilateral\s+signing).{0,50}?(exceed|above|more\s+than|over)\b",
        Severity.P2, Regulation.SOX,
        "Unilateral signing or single signature approval above corporate thresholds violates separation of duties controls.",
        "Enforce multi-party approval workflows for values exceeding standard thresholds.",
    ),
]


def _excerpt(text: str, start: int, end: int, pad: int = 50) -> str:
    s = max(0, start - pad)
    e = min(len(text), end + pad)
    
    left_newline = text.rfind("\n", s, start)
    if left_newline != -1:
        s = left_newline + 1
        
    right_newline = text.find("\n", end, e)
    if right_newline != -1:
        e = right_newline
        
    return text[s:e]


def run_rules(text: str) -> List[Violation]:
    found: List[Violation] = []
    seen = set()
    for rule in RULES:
        if rule.rid == "R-CLASS":
            # whole-document check: only fire once if no label anywhere
            if not re.search(r"\b(public|internal|confidential|restricted)\b",
                             text, re.IGNORECASE):
                found.append(Violation(
                    id=f"v_{uuid.uuid4().hex[:8]}",
                    title=rule.title, severity=rule.severity,
                    source_regulation=rule.regulation, detected_by="rule_engine",
                    excerpt=text[:50].strip() if text else "(no classification label found in document)",
                    explanation=rule.explanation, recommendation=rule.recommendation,
                ))
            continue
        for m in rule.pattern.finditer(text):
            # Programmatic checksum guardrails to prevent aggressive false positives
            if rule.rid == "R-PII-AADHAAR":
                if not validate_aadhaar(m.group(0)):
                    continue
            elif rule.rid == "R-PII-CREDITCARD":
                if not validate_credit_card(m.group(0)):
                    continue
                    
            key = (rule.rid, m.group(0).lower()[:60])
            if key in seen:
                continue
            seen.add(key)
            found.append(Violation(
                id=f"v_{uuid.uuid4().hex[:8]}",
                title=rule.title, severity=rule.severity,
                source_regulation=rule.regulation, detected_by="rule_engine",
                excerpt=_excerpt(text, m.start(), m.end()),
                explanation=rule.explanation, recommendation=rule.recommendation,
            ))
            if rule.rid in ("R-PII-EMAIL", "R-PII-PHONE") and \
                    sum(1 for v in found if v.title == rule.title) >= 3:
                break  # cap repetitive PII hits


    # Dynamic Custom Policy Checks
    try:
        from app import db
        custom_policies = db.list_custom_policies()
        for cp in custom_policies:
            policy_name = cp["policy_name"]
            for idx, rule in enumerate(cp["rules"]):
                rule_lower = rule.lower()
                
                # Check 1: proxy.nexus.internal routing check
                if "proxy.nexus.internal" in rule_lower:
                    urls = re.findall(r"https?://[a-zA-Z0-9./_-]+", text)
                    for url in urls:
                        if "proxy.nexus.internal" not in url:
                            found.append(Violation(
                                id=f"v_custom_{uuid.uuid4().hex[:8]}",
                                title=f"Custom Policy: {policy_name}",
                                severity=Severity.P2,
                                source_regulation=Regulation.CUSTOM,
                                detected_by="Internal Policy Agent",
                                excerpt=url,
                                explanation=f"The endpoint '{url}' violates the custom policy rule: '{rule}'",
                                recommendation="Route this endpoint through proxy.nexus.internal.",
                            ))
                
                # Check 2: generic 'no [word] allowed' constraint check
                match_no = re.search(r"no\s+([a-zA-Z0-9_-]+)\s+allowed", rule_lower)
                if match_no:
                    word = match_no.group(1)
                    if word in text.lower():
                        for m in re.finditer(re.escape(word), text, re.IGNORECASE):
                            found.append(Violation(
                                id=f"v_custom_{uuid.uuid4().hex[:8]}",
                                title=f"Custom Policy: {policy_name}",
                                severity=Severity.P2,
                                source_regulation=Regulation.CUSTOM,
                                detected_by="Internal Policy Agent",
                                excerpt=_excerpt(text, m.start(), m.end(), pad=20),
                                explanation=f"Found restricted content '{m.group(0)}', violating the rule: '{rule}'",
                                recommendation=f"Redact or remove reference to '{m.group(0)}'.",
                            ))
                            break
    except Exception as e:
        print(f"[rules] Error running custom rules: {e}")

    return found
