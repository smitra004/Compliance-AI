"""Backend-Driven Enterprise Resource Catalog Service."""
from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class EnterpriseResource(BaseModel):
    resource_id: str
    name: str
    category: str  # Documents, Dashboards, APIs, Reports, Datasets
    classification: str  # Public, Internal, Confidential, Restricted, Top Secret
    department: str
    contains_pii: bool = False
    contains_financial_data: bool = False
    owner: str = "security-admin@acmecorp.com"
    raw_content: str = ""


# Master Enterprise Catalog Data
CATALOG_DATA: List[EnterpriseResource] = [
    EnterpriseResource(
        resource_id="RES-DOC-101",
        name="Q3 Financial Audit Ledger & Executive Bonus Matrix",
        category="Documents",
        classification="Restricted",
        department="Finance",
        contains_pii=True,
        contains_financial_data=True,
        owner="finance-audit@acmecorp.com",
        raw_content="CONFIDENTIAL FINANCIAL LEDGER\n\nExecutive Bonus Approval Matrix Q3 2026.\nEmployee PAN: ABCDE1234F | Aadhaar: 2345 6789 0123\nContact Email: executive.finance@acmecorp.com | Phone: +1-555-019-2834\n\nTotal Budget Allocation: $4,850,000.\nAudit Verdict: Pending Internal Review.",
    ),
    EnterpriseResource(
        resource_id="RES-DOC-102",
        name="Employee Compensation & Medical Benefits Records",
        category="Documents",
        classification="Confidential",
        department="HR",
        contains_pii=True,
        contains_financial_data=False,
        owner="hr-benefits@acmecorp.com",
        raw_content="HUMAN RESOURCES RECORD\n\nAnnual Employee Benefits & Health Claims 2026.\nEmployee SSN / PAN: FGHIJ5678K | Aadhaar: 9876 5432 1098\nContact Email: hr.employee@acmecorp.com\n\nCoverage Plan: Executive Premium.",
    ),
    EnterpriseResource(
        resource_id="RES-DOC-103",
        name="Core Infrastructure Penetration Test & Vulnerability Audit",
        category="Documents",
        classification="Top Secret",
        department="Security",
        contains_pii=False,
        contains_financial_data=False,
        owner="sec-ops@acmecorp.com",
        raw_content="TOP SECRET SECURITY REPORT\n\nSystem Penetration Test Results - Production Cluster.\nDiscovered Open Endpoints: 3 | Critical Patch Status: Applied.\nSecurity Clearance Boundary: Level 5 (Top Secret) Required.",
    ),
    EnterpriseResource(
        resource_id="RES-DSH-201",
        name="Global Revenue & Tax Compliance Analytics Dashboard",
        category="Dashboards",
        classification="Restricted",
        department="Finance",
        contains_pii=False,
        contains_financial_data=True,
        owner="finance-bi@acmecorp.com",
        raw_content="DASHBOARD METRICS\n\nQ3 Tax Reserves: $12.4M | Unreconciled Transactions: 14\nRegion Rollup: Global / EU / APAC / US.",
    ),
    EnterpriseResource(
        resource_id="RES-API-301",
        name="Customer PII Export REST API Service",
        category="APIs",
        classification="Confidential",
        department="IT",
        contains_pii=True,
        contains_financial_data=False,
        owner="api-gateways@acmecorp.com",
        raw_content="API ENDPOINT DEFINITION\n\nPOST /api/v1/customers/export-pii\nPayload schema: { user_id, email, phone, pan_number }\nRate Limit: 10 req/min.",
    ),
    EnterpriseResource(
        resource_id="RES-RPT-401",
        name="GDPR Article 30 Processing Activity Log Report",
        category="Reports",
        classification="Confidential",
        department="Legal",
        contains_pii=True,
        contains_financial_data=False,
        owner="legal-privacy@acmecorp.com",
        raw_content="LEGAL REGULATORY REPORT\n\nEU GDPR Article 28 & 30 Data Controller Processing Log.\nData Subjects Impacted: 140,000.\nSignatory Email: privacy.officer@acmecorp.com",
    ),
    EnterpriseResource(
        resource_id="RES-DAT-501",
        name="Anonymized User Behavioral Analytics Dataset",
        category="Datasets",
        classification="Internal",
        department="Operations",
        contains_pii=False,
        contains_financial_data=False,
        owner="data-science@acmecorp.com",
        raw_content="DATASET CATALOG\n\nTable: user_session_analytics_2026\nRows: 1.2M | Size: 420MB\nData Anonymization Hash: SHA-256 applied.",
    ),
    EnterpriseResource(
        resource_id="RES-DOC-104",
        name="Company Global Travel & Expense Policy 2026",
        category="Documents",
        classification="Public",
        department="General",
        contains_pii=False,
        contains_financial_data=False,
        owner="policy-desk@acmecorp.com",
        raw_content="PUBLIC POLICY\n\nGlobal Employee Expense & Travel Policy 2026.\nPer Diem Allowance: $75/day.\nAccess Boundary: Public (All Employees Cleared).",
    ),
]


class ResourceService:
    """Service managing backend-driven Enterprise Resource Catalog."""

    @staticmethod
    def get_catalog(
        category: Optional[str] = None,
        search: Optional[str] = None,
        department: Optional[str] = None,
    ) -> List[EnterpriseResource]:
        results = list(CATALOG_DATA)

        if category and category.lower() != "all":
            results = [r for r in results if r.category.lower() == category.lower()]

        if department and department.lower() != "all":
            results = [r for r in results if r.department.lower() == department.lower()]

        if search and search.strip():
            q = search.strip().lower()
            results = [
                r for r in results
                if q in r.name.lower() or q in r.resource_id.lower() or q in r.department.lower()
            ]

        return results

    @staticmethod
    def get_resource_by_id(resource_id: str) -> Optional[EnterpriseResource]:
        return next((r for r in CATALOG_DATA if r.resource_id.lower() == resource_id.lower()), None)


resource_service = ResourceService()
