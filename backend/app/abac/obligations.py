"""Obligations Processor and Field-Level Data Masking Service."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Union


def mask_sensitive_value(key: str, val: Any) -> Any:
    """Applies field-level masking rules depending on attribute key name."""
    if val is None or not isinstance(val, (str, int, float)):
        return val

    s_key = str(key).lower()
    s_val = str(val).strip()

    if not s_val:
        return s_val

    # PAN Card (India: e.g., ABCDE1234F -> ABCDE****F)
    if "pan" in s_key or "ssn" in s_key or "tax_id" in s_key:
        if len(s_val) >= 5:
            return s_val[:3] + "*" * (len(s_val) - 4) + s_val[-1]
        return "[MASKED-TAX-ID]"

    # Aadhaar / National ID (12 digits -> XXXX-XXXX-1234)
    if "aadhaar" in s_key or "national_id" in s_key or "id_number" in s_key:
        if len(s_val) >= 4:
            return "XXXX-XXXX-" + s_val[-4:]
        return "[MASKED-ID]"

    # Phone Number (e.g. +1-555-0199 -> XXX-XXX-0199)
    if "phone" in s_key or "mobile" in s_key or "contact" in s_key:
        if len(s_val) >= 4:
            return "XXX-XXX-" + s_val[-4:]
        return "[MASKED-PHONE]"

    # Email address (johndoe@example.com -> j***e@example.com)
    if "email" in s_key:
        if "@" in s_val:
            user_part, domain = s_val.split("@", 1)
            if len(user_part) > 2:
                masked_user = user_part[0] + "***" + user_part[-1]
            else:
                masked_user = user_part[0] + "***"
            return f"{masked_user}@{domain}"
        return "[MASKED-EMAIL]"

    # Salary / Compensation / Financial amounts
    if "salary" in s_key or "compensation" in s_key or "bank_account" in s_key or "credit_card" in s_key:
        if "salary" in s_key or "compensation" in s_key:
            return s_val  # Salary visible if permitted by rule
        return "[MASKED-FINANCIAL-DATA]"

    return s_val


def mask_data_payload(payload: Union[Dict[str, Any], List[Any]]) -> Union[Dict[str, Any], List[Any]]:
    """Recursively traverses payload dict/list and applies field-level masking."""
    if isinstance(payload, dict):
        masked_dict = {}
        for k, v in payload.items():
            if k.lower() in ("pan", "aadhaar", "ssn", "phone", "mobile", "national_id", "credit_card"):
                masked_dict[k] = mask_sensitive_value(k, v)
            elif isinstance(v, (dict, list)):
                masked_dict[k] = mask_data_payload(v)
            else:
                masked_dict[k] = v
        return masked_dict
    elif isinstance(payload, list):
        return [mask_data_payload(item) for item in payload]
    return payload


class ObligationsProcessor:
    """Processes obligations returned by ABAC evaluation."""

    @staticmethod
    def process_obligations(obligations: List[str], data: Optional[Union[Dict[str, Any], List[Any]]] = None) -> Tuple[List[str], Optional[Union[Dict[str, Any], List[Any]]]]:
        processed_flags = list(obligations)
        masked_data = data

        if "Mask Sensitive Fields" in obligations and data is not None:
            masked_data = mask_data_payload(data)

        return processed_flags, masked_data
