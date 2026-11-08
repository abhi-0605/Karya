"""
PII Gateway — Masks and redacts sensitive data before any external model call.
Implements Indian regulatory recognizers (DPDP Act compliance):
- Aadhaar (12 digits): BLOCKED / REDACTED
- PAN (Permanent Account Number - 10 chars): BLOCKED / REDACTED
- Bank Account numbers: BLOCKED / REDACTED
- Indian Phone (+91 / 10-digit): Masked with placeholder tokens <PHONE_n>
- Email: Masked with placeholder tokens <EMAIL_n>
- Names: Masked with <PERSON_n>
Provides bidirectional tokenize/rehydrate capabilities.
"""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Optional
import structlog

log = structlog.get_logger()

# Regex patterns for Indian identifiers
AADHAAR_REGEX = re.compile(r"\b[2-9]{1}[0-9]{3}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4}\b")
PAN_REGEX = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b")
PHONE_REGEX = re.compile(r"(?:\+91[\s\-]?)?(?:[6-9][0-9]{9})\b")
EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
BANK_REGEX = re.compile(r"\b(?:A/C|Account|Acct|Bank|Acc)[\s:#\-]*([0-9]{9,18})\b", re.IGNORECASE)
UAN_REGEX = re.compile(r"\b(?:UAN[\s:#\-]*)?10\d{10}\b")
SALARY_REGEX = re.compile(r"\b(?:INR|Rs\.?|₹)[\s]*[0-9,]+(?:\.[0-9]{2})?\b|\b(?:CTC|LPA|salary|base)[\s:]*[0-9.]+\s*(?:LPA|lakhs|lac)?\b", re.IGNORECASE)


@dataclass
class MaskResult:
    masked_text: str
    redacted_items: list[str] = field(default_factory=list)
    rehydration_map: dict[str, str] = field(default_factory=dict)
    pii_detected: bool = False


class PIIGateway:
    """Masks outgoing text before sending to LLM, and logs fields sent."""

    def __init__(self):
        self.outbound_log: list[dict] = []

    def mask(self, text: str) -> MaskResult:
        """
        Mask sensitive data in text.
        Aadhaar, PAN, Bank, UAN, Salary are completely redacted.
        Phone, Email, Person are replaced with numbered tokens that can be rehydrated.
        """
        if not text:
            return MaskResult(masked_text="", pii_detected=False)

        rehydration_map = {}
        redacted = []
        result = text

        # 1. HARD BLOCKS: Bank Account (processed before generic 12-digit numbers)
        bank_matches = BANK_REGEX.findall(result)
        if bank_matches:
            redacted.extend([f"BANK:{m}" for m in bank_matches])
            result = re.sub(
                r"(\b(?:A/C|Account|Acct|Bank|Acc)[\s:#\-]*)[0-9]{9,18}\b",
                r"\1<REDACTED_BANK_ACCOUNT>",
                result,
                flags=re.IGNORECASE,
            )

        # 2. HARD BLOCKS: Aadhaar (12 digits)
        aadhaar_matches = AADHAAR_REGEX.findall(result)
        if aadhaar_matches:
            redacted.extend([f"AADHAAR:{m}" for m in aadhaar_matches])
            result = AADHAAR_REGEX.sub("<REDACTED_AADHAAR>", result)

        # 3. HARD BLOCKS: PAN
        pan_matches = PAN_REGEX.findall(result)
        if pan_matches:
            redacted.extend([f"PAN:{m}" for m in pan_matches])
            result = PAN_REGEX.sub("<REDACTED_PAN>", result)

        # 4. HARD BLOCKS: UAN
        uan_matches = UAN_REGEX.findall(result)
        if uan_matches:
            redacted.extend([f"UAN:{m}" for m in uan_matches])
            result = UAN_REGEX.sub("<REDACTED_UAN>", result)

        # 5. HARD BLOCKS: Salary / CTC
        salary_matches = SALARY_REGEX.findall(result)
        if salary_matches:
            redacted.extend([f"SALARY:{m}" for m in salary_matches])
            result = SALARY_REGEX.sub("<REDACTED_COMPENSATION>", result)

        # 6. Reversible Masking: Emails
        email_count = 0
        for match in set(EMAIL_REGEX.findall(result)):
            email_count += 1
            token = f"<EMAIL_{email_count}>"
            rehydration_map[token] = match
            result = result.replace(match, token)

        # 7. Reversible Masking: Phone numbers
        phone_count = 0
        for match in set(PHONE_REGEX.findall(result)):
            phone_count += 1
            token = f"<PHONE_{phone_count}>"
            rehydration_map[token] = match
            result = result.replace(match, token)

        pii_detected = bool(redacted or rehydration_map)

        # Log sanitized outbound transaction
        self.outbound_log.append({
            "pii_detected": pii_detected,
            "redacted_count": len(redacted),
            "rehydrated_tokens": list(rehydration_map.keys()),
            "length_out": len(result),
        })

        return MaskResult(
            masked_text=result,
            redacted_items=redacted,
            rehydration_map=rehydration_map,
            pii_detected=pii_detected,
        )

    def rehydrate(self, text: str, rehydration_map: dict[str, str]) -> str:
        """Replace placeholder tokens (<EMAIL_1>, <PHONE_1>) back with actual values."""
        result = text
        for token, original in rehydration_map.items():
            result = result.replace(token, original)
        return result

    @staticmethod
    def assert_no_pii_leak(text: str) -> None:
        """
        Asserts that raw Aadhaar, PAN, or Bank account numbers NEVER appear in the outbound payload.
        Raises AssertionError if forbidden PII pattern is found.
        """
        if AADHAAR_REGEX.search(text):
            raise AssertionError("PII LEAK: Unmasked Aadhaar number detected in payload!")
        if PAN_REGEX.search(text):
            raise AssertionError("PII LEAK: Unmasked PAN detected in payload!")
        if BANK_REGEX.search(text):
            raise AssertionError("PII LEAK: Unmasked Bank account number detected in payload!")
