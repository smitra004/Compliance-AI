"""Enterprise Dynamic Risk Engine for Risk-Adaptive Access Control (RACK)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.abac.attributes.subject import SubjectAttributes
from app.abac.attributes.environment import EnvironmentAttributes


class RiskFactorResult(BaseModel):
    factor: str
    score: int
    description: str
    passed: bool


class RiskAnalysis(BaseModel):
    final_score: int
    risk_level: str  # Low, Medium, High, Critical
    breakdown: List[RiskFactorResult]
    summary: str


class EnterpriseRiskEngine:
    """Calculates dynamic contextual risk score with transparent, auditable factor scoring."""

    @staticmethod
    def calculate(subject: SubjectAttributes, env: EnvironmentAttributes) -> RiskAnalysis:
        breakdown: List[RiskFactorResult] = []
        total_score = subject.risk_score

        # 1. Base User Account Risk
        if subject.risk_score > 0:
            breakdown.append(
                RiskFactorResult(
                    factor="Base User Account Risk",
                    score=subject.risk_score,
                    description=f"Initial risk baseline assigned to user profile ({subject.risk_score})",
                    passed=False,
                )
            )
        else:
            breakdown.append(
                RiskFactorResult(
                    factor="Base User Account Risk",
                    score=0,
                    description="User account baseline risk is clean",
                    passed=True,
                )
            )

        # 2. Corporate VPN & Office Network Connection
        if not env.vpn_connected and not env.office_network:
            total_score += 20
            breakdown.append(
                RiskFactorResult(
                    factor="VPN / Network Connection",
                    score=20,
                    description="Request originated outside Corporate VPN and Office Network",
                    passed=False,
                )
            )
        else:
            breakdown.append(
                RiskFactorResult(
                    factor="VPN / Network Connection",
                    score=0,
                    description="Corporate VPN or trusted internal office network verified",
                    passed=True,
                )
            )

        # 3. Multi-Factor Authentication (MFA)
        if not subject.mfa_status:
            total_score += 25
            breakdown.append(
                RiskFactorResult(
                    factor="MFA Verification",
                    score=25,
                    description="Multi-factor authentication (MFA) not verified for this session",
                    passed=False,
                )
            )
        else:
            breakdown.append(
                RiskFactorResult(
                    factor="MFA Verification",
                    score=0,
                    description="Session authenticated with strong MFA",
                    passed=True,
                )
            )

        # 4. Business Hours & Weekend Context
        if not env.business_hours:
            total_score += 15
            breakdown.append(
                RiskFactorResult(
                    factor="Business Hours",
                    score=15,
                    description="Access attempt outside configured organizational business hours",
                    passed=False,
                )
            )
        else:
            breakdown.append(
                RiskFactorResult(
                    factor="Business Hours",
                    score=0,
                    description="Access attempt occurred within standard business hours",
                    passed=True,
                )
            )

        if env.weekend:
            total_score += 5
            breakdown.append(
                RiskFactorResult(
                    factor="Weekend Access",
                    score=5,
                    description="Access attempt occurred on a weekend",
                    passed=False,
                )
            )

        # 5. Device Trust & Management Status
        device_trusted = subject.device_trust_level.lower() == "trusted" and env.device_managed
        if not device_trusted:
            total_score += 15
            breakdown.append(
                RiskFactorResult(
                    factor="Device Compliance & Trust",
                    score=15,
                    description="Endpoint device is unmanaged or holds untrusted status",
                    passed=False,
                )
            )
        else:
            breakdown.append(
                RiskFactorResult(
                    factor="Device Compliance & Trust",
                    score=0,
                    description="Managed, fully compliant corporate device verified",
                    passed=True,
                )
            )

        # 6. IP Reputation & Geolocation Risk
        country_code = (env.country or "US").upper()
        if country_code not in ("US", "EU", "GLOBAL", "GB", "CA", "DE", "FR", "AU"):
            total_score += 20
            breakdown.append(
                RiskFactorResult(
                    factor="Origin Country / Geolocation",
                    score=20,
                    description=f"Request originated from non-standard region ({country_code})",
                    passed=False,
                )
            )
        else:
            breakdown.append(
                RiskFactorResult(
                    factor="Origin Country / Geolocation",
                    score=0,
                    description=f"Request originated from approved geographic zone ({country_code})",
                    passed=True,
                )
            )

        # 7. Failed Login Attempts
        if subject.failed_login_attempts >= 3:
            total_score += 40
            breakdown.append(
                RiskFactorResult(
                    factor="Failed Login Attempts",
                    score=40,
                    description=f"Account recorded {subject.failed_login_attempts} recent failed authentication attempts",
                    passed=False,
                )
            )
        elif subject.failed_login_attempts > 0:
            added = subject.failed_login_attempts * 10
            total_score += added
            breakdown.append(
                RiskFactorResult(
                    factor="Failed Login Attempts",
                    score=added,
                    description=f"Account recorded {subject.failed_login_attempts} minor failed authentication attempt(s)",
                    passed=False,
                )
            )

        # 8. Request Velocity & Frequency Anomaly
        if env.request_frequency > 30:
            total_score += 20
            breakdown.append(
                RiskFactorResult(
                    factor="Request Frequency Anomaly",
                    score=20,
                    description=f"High API invocation velocity detected ({env.request_frequency} req/min)",
                    passed=False,
                )
            )

        final_score = min(max(total_score, 0), 100)

        # Classify risk level
        if final_score < 30:
            risk_level = "Low"
        elif final_score < 60:
            risk_level = "Medium"
        elif final_score < 80:
            risk_level = "High"
        else:
            risk_level = "Critical"

        summary = (
            f"Calculated composite risk score is {final_score}/100 ({risk_level} Risk Level) "
            f"across {len(breakdown)} evaluated environmental & identity vectors."
        )

        return RiskAnalysis(
            final_score=final_score,
            risk_level=risk_level,
            breakdown=breakdown,
            summary=summary,
        )


risk_engine = EnterpriseRiskEngine()
