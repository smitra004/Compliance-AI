"""CrewAI crew: a second, independent multi-agent layer that runs *after*
the scan pipeline (GDPR/Security/Legal/Policy council + rule engine) has
already produced grounded findings. Where the council in `agents.py`
extracts violations, this crew's job is judgment on top of those violations:
a Risk Assessor prioritizes them by business impact and a Remediation
Advisor drafts an executive summary and action plan — the kind of synthesis
step a human compliance lead would do after reading the raw findings.

Runs for real (calls the configured LLM) when a key is present; otherwise
falls back to a deterministic templated narrative built from the same
violation data, so `/api/scan/{id}/crew-analysis` never returns empty.
"""
from __future__ import annotations

from typing import Any, Dict, List

from app import config
from app.models import ScanRecord


def _fallback_narrative(record: ScanRecord) -> Dict[str, Any]:
    by_sev = {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    for v in record.violations:
        by_sev[v.severity.value if hasattr(v.severity, "value") else str(v.severity)] = \
            by_sev.get(v.severity.value if hasattr(v.severity, "value") else str(v.severity), 0) + 1

    top = sorted(record.violations, key=lambda v: v.severity.value if hasattr(v.severity, "value") else str(v.severity))[:3]

    return {
        "engine": "fallback-deterministic",
        "executive_summary": (
            f"{record.document_name} scored {record.compliance_score}/100 with "
            f"{record.total_violations} finding(s) ({by_sev['P1']} critical, {by_sev['P2']} high, "
            f"{by_sev['P3']} medium, {by_sev['P4']} low). "
            + ("Immediate remediation recommended before external distribution." if by_sev["P1"] else
               "No critical blockers; address remaining items on the standard remediation cadence.")
        ),
        "priority_actions": [
            {"title": v.title, "severity": v.severity.value if hasattr(v.severity, "value") else str(v.severity),
             "recommendation": v.recommendation}
            for v in top
        ],
    }


async def run_crew_analysis(record: ScanRecord) -> Dict[str, Any]:
    if not config.CREW_ANALYSIS_ENABLED or config.DEMO_MODE:
        return _fallback_narrative(record)

    try:
        from crewai import Agent, Task, Crew, Process
        from app.pipeline.agents import _get_llm_client

        llm = _get_llm_client(config.ANALYSIS_MODEL, temperature=0.2)

        risk_assessor = Agent(
            role="Risk Assessor",
            goal="Rank compliance violations by real-world business and regulatory impact",
            backstory="A former Big-4 compliance risk consultant who has triaged thousands of audit findings.",
            llm=llm, verbose=False,
        )
        remediation_advisor = Agent(
            role="Remediation Advisor",
            goal="Turn ranked findings into a short, board-ready action plan",
            backstory="Writes executive summaries that get read in 30 seconds and acted on.",
            llm=llm, verbose=False,
        )

        findings_text = "\n".join(
            f"- [{v.severity.value if hasattr(v.severity, 'value') else v.severity}] {v.title}: {v.description}"
            for v in record.violations
        ) or "No violations found."

        rank_task = Task(
            description=f"Rank these compliance findings for '{record.document_name}' by business impact:\n{findings_text}",
            expected_output="A ranked list of the top findings with one-line impact justification each.",
            agent=risk_assessor,
        )
        summary_task = Task(
            description="Using the ranked findings, write a 3-sentence executive summary and 3 concrete next actions.",
            expected_output="Executive summary (3 sentences) + numbered action list.",
            agent=remediation_advisor,
            context=[rank_task],
        )

        crew = Crew(agents=[risk_assessor, remediation_advisor], tasks=[rank_task, summary_task], process=Process.sequential)

        # crew.kickoff() is a blocking sync call, so we can't reuse the async
        # _call_llm_with_retry helper here — but it hits the same Groq
        # free-tier rate limits as the main scan pipeline, so it needs the
        # same backoff-and-retry treatment rather than falling back to the
        # deterministic narrative on the first transient 429.
        import time, random
        from app.pipeline.agents import _is_rate_limit_error

        max_retries = 5
        last_exc: Exception | None = None
        result = None
        for attempt in range(max_retries + 1):
            try:
                result = crew.kickoff()
                last_exc = None
                break
            except Exception as retry_exc:
                last_exc = retry_exc
                if not _is_rate_limit_error(retry_exc) or attempt == max_retries:
                    raise
                delay = 3 * (2 ** attempt) + random.uniform(0, 1)
                print(f"[crew] 429 rate limit hit (attempt {attempt + 1}/{max_retries}); "
                      f"backing off {delay:.1f}s before retrying.")
                time.sleep(delay)
        if last_exc is not None:
            raise last_exc

        return {"engine": "crewai", "executive_summary": str(result), "priority_actions": []}
    except Exception as e:  # noqa: BLE001
        print(f"[crew] CrewAI run failed ({e}); using deterministic fallback")
        return _fallback_narrative(record)
