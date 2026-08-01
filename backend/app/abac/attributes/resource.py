"""Resource attributes resolution module."""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ResourceAttributes(BaseModel):
    resource_id: str = "RES-001"
    owner: str = "admin"
    department: str = "General"
    classification: str = "Internal"  # Public, Internal, Confidential, Highly Confidential, Restricted, Top Secret
    sensitivity: str = "Medium"        # Low, Medium, High, Critical
    confidentiality: str = "Standard"
    compliance_status: str = "Scanned"
    version: str = "1.0"
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    region: str = "Global"              # Global, EU, US, APAC
    regulation: str = "custom"          # gdpr, iso27001, sox, internal_security, internal_hr, custom
    contains_pii: bool = False
    contains_financial_data: bool = False
    contains_hipaa_data: bool = False
    contains_pci_data: bool = False
    encryption_enabled: bool = True
    retention_policy: str = "7_Years"
    approval_status: str = "Approved"
    document_type: str = "Policy"       # Policy, Report, Code, Contract, Financial, Payroll
    business_unit: str = "Corporate"

    @property
    def classification_rank(self) -> int:
        from app.abac.attributes.subject import CLEARANCE_HIERARCHY
        key = self.classification.lower().replace(" ", "_")
        return CLEARANCE_HIERARCHY.get(key, 1)


def extract_resource_attributes(res: Optional[Dict[str, Any]] = None, custom_overrides: Optional[Dict[str, Any]] = None) -> ResourceAttributes:
    """Extracts and normalizes document/resource attributes."""
    merged = {}
    if res:
        merged = {
            "resource_id": str(res.get("scan_id") or res.get("id") or res.get("resource_id") or "RES-001"),
            "owner": res.get("uploaded_by") or res.get("owner") or "admin",
            "department": res.get("department") or "General",
            "classification": res.get("classification") or "Internal",
            "sensitivity": res.get("sensitivity") or ("High" if res.get("contains_pii") or res.get("contains_financial_data") else "Medium"),
            "confidentiality": res.get("confidentiality") or "Standard",
            "compliance_status": res.get("compliance_status") or "Scanned",
            "version": str(res.get("version") or "1.0"),
            "created_date": str(res.get("created_at") or res.get("created_date") or ""),
            "modified_date": str(res.get("modified_date") or ""),
            "region": res.get("region") or "Global",
            "regulation": str(res.get("regulation") or res.get("source_regulation") or "custom").lower(),
            "contains_pii": bool(res.get("contains_pii", False)),
            "contains_financial_data": bool(res.get("contains_financial_data", False)),
            "contains_hipaa_data": bool(res.get("contains_hipaa_data", False)),
            "contains_pci_data": bool(res.get("contains_pci_data", False)),
            "encryption_enabled": bool(res.get("encryption_enabled", True)),
            "retention_policy": res.get("retention_policy") or "7_Years",
            "approval_status": res.get("approval_status") or "Approved",
            "document_type": res.get("document_type") or "Policy",
            "business_unit": res.get("business_unit") or "Corporate",
        }

    if custom_overrides:
        for k, v in custom_overrides.items():
            if v is not None and k in ResourceAttributes.model_fields:
                merged[k] = v

    return ResourceAttributes(**merged)
