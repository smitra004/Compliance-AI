"""Real Field-Level Data Masking & Obligations Enforcement Service."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Union


class MaskingService:
    """Enforces field-level redaction and obligation constraints on responses."""

    # Regex patterns for sensitive data fields
    PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b|\b(?:\d[ -]*?){13,16}\b")
    AADHAAR_REGEX = re.compile(r"\b[2-9]{1}\d{3}\s?\d{4}\s?\d{4}\b")
    PHONE_REGEX = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")

    @staticmethod
    def mask_text(text: str, obligations: List[str]) -> str:
        """Applies field-level regex masking to text content based on active obligations."""
        if not text or not isinstance(text, str):
            return text

        result = text

        # 1. Mask PAN / Credit Card Numbers
        if any(ob.lower() in ("mask pan", "mask credit card", "mask_pan") for ob in obligations) or True:
            result = MaskingService.PAN_REGEX.sub(lambda m: MaskingService._mask_pan_match(m.group(0)), result)

        # 2. Mask Aadhaar Numbers
        if any(ob.lower() in ("mask aadhaar", "mask_aadhaar") for ob in obligations) or True:
            result = MaskingService.AADHAAR_REGEX.sub("XXXX-XXXX-5678", result)

        # 3. Hide Phone Numbers
        if any(ob.lower() in ("hide phone", "mask phone", "hide_phone") for ob in obligations):
            result = MaskingService.PHONE_REGEX.sub("+X-XXX-XXX-9999", result)

        # 4. Hide Email Addresses
        if any(ob.lower() in ("hide email", "mask email", "hide_email") for ob in obligations):
            result = MaskingService.EMAIL_REGEX.sub(lambda m: MaskingService._mask_email_match(m.group(0)), result)

        return result

    @staticmethod
    def _mask_pan_match(val: str) -> str:
        clean = val.replace("-", "").replace(" ", "")
        if len(clean) >= 4:
            return f"XXXX-XXXX-XXXX-{clean[-4:]}"
        return "XXXX-XXXX-XXXX-1234"

    @staticmethod
    def _mask_email_match(email: str) -> str:
        if "@" in email:
            name, domain = email.split("@", 1)
            if len(name) > 2:
                masked_name = name[0] + "***" + name[-1]
            else:
                masked_name = name[0] + "***"
            return f"{masked_name}@{domain}"
        return "u***r@domain.com"

    @staticmethod
    def enforce_on_payload(payload: Union[Dict[str, Any], List[Any]], obligations: List[str]) -> Dict[str, Any]:
        """Deeply enforces data masking and UI restriction flags on an outgoing payload."""
        result_payload = payload if isinstance(payload, dict) else {"data": payload}

        # 1. Evaluate restriction flags
        can_download = not any("disable download" in ob.lower() or "read only" in ob.lower() for ob in obligations)
        can_export = not any("disable export" in ob.lower() or "read only" in ob.lower() for ob in obligations)
        can_print = not any("disable print" in ob.lower() or "read only" in ob.lower() for ob in obligations)

        # 2. Recursively mask text in dictionary or list
        masked_data = MaskingService._recursive_mask(result_payload, obligations)

        if isinstance(masked_data, dict):
            masked_data["obligations_applied"] = obligations
            masked_data["enforcement_flags"] = {
                "can_download": can_download,
                "can_export": can_export,
                "can_print": can_print,
            }
            return masked_data
        
        return {
            "data": masked_data,
            "obligations_applied": obligations,
            "enforcement_flags": {
                "can_download": can_download,
                "can_export": can_export,
                "can_print": can_print,
            },
        }

    @staticmethod
    def _recursive_mask(obj: Any, obligations: List[str]) -> Any:
        if isinstance(obj, str):
            return MaskingService.mask_text(obj, obligations)
        elif isinstance(obj, dict):
            return {k: MaskingService._recursive_mask(v, obligations) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [MaskingService._recursive_mask(item, obligations) for item in obj]
        return obj


masking_service = MaskingService()
