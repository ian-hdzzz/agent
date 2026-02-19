"""
Gobierno Queretaro - Mexican PII Pattern Detection
Regex patterns for detecting sensitive information in text
"""

import re
from typing import Literal

# Type definitions for PII categories
PIIType = Literal[
    "CURP",
    "RFC",
    "PHONE_MX",
    "CONTRACT_CEA",
    "EMAIL",
    "CREDIT_CARD",
    "INE",
    "PASSPORT",
    "NSS",
    "ADDRESS",
]

# Mexican PII regex patterns
PII_PATTERNS: dict[PIIType, re.Pattern] = {
    # CURP: 18 characters - AAAA000000HAAAAA00
    # Format: 4 letters + 6 digits (birthdate) + H/M (gender) + 5 letters (state) + 2 alphanumeric
    "CURP": re.compile(
        r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z\d]{2}\b",
        re.IGNORECASE,
    ),
    # RFC: 12-13 characters for individuals, 12 for companies
    # Format: 3-4 letters + 6 digits (date) + 3 alphanumeric (homoclave)
    "RFC": re.compile(
        r"\b[A-Z&Ñ]{3,4}\d{6}[A-Z\d]{3}\b",
        re.IGNORECASE,
    ),
    # Mexican phone numbers with various formats
    # Supports: +52, country code, area codes, extensions
    "PHONE_MX": re.compile(
        r"(?:\+?52)?[\s.-]?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}\b",
    ),
    # CEA water contract numbers (6-10 digits)
    "CONTRACT_CEA": re.compile(
        r"\b(?:contrato|cuenta|numero de cuenta|no\.? de cuenta)?\s*[:#]?\s*(\d{6,10})\b",
        re.IGNORECASE,
    ),
    # Email addresses
    "EMAIL": re.compile(
        r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
    ),
    # Credit card numbers (13-19 digits with optional separators)
    "CREDIT_CARD": re.compile(
        r"\b(?:\d{4}[\s.-]?){3,4}\d{1,4}\b",
    ),
    # INE voter ID (13 or 18 characters)
    "INE": re.compile(
        r"\b(?:INE|IFE|credencial)?\s*[:#]?\s*([A-Z]{6}\d{8}[HM]\d{3}|\d{13})\b",
        re.IGNORECASE,
    ),
    # Mexican passport (alphanumeric, typically starts with G followed by 8 digits)
    "PASSPORT": re.compile(
        r"\b[A-Z]\d{8}\b",
        re.IGNORECASE,
    ),
    # NSS - Social Security Number (11 digits)
    "NSS": re.compile(
        r"\b(?:NSS|IMSS|seguro social)?\s*[:#]?\s*(\d{11})\b",
        re.IGNORECASE,
    ),
    # Address patterns (simplified - captures common Mexican address formats)
    "ADDRESS": re.compile(
        r"\b(?:calle|av(?:enida)?|blvd|col(?:onia)?|fracc(?:ionamiento)?)\s+[A-Za-z0-9\s,#.-]+(?:\d{5})?\b",
        re.IGNORECASE,
    ),
}

# Masking templates for each PII type
MASK_TEMPLATES: dict[PIIType, str] = {
    "CURP": "[CURP_REDACTED]",
    "RFC": "[RFC_REDACTED]",
    "PHONE_MX": "[PHONE_REDACTED]",
    "CONTRACT_CEA": "[CONTRACT_REDACTED]",
    "EMAIL": "[EMAIL_REDACTED]",
    "CREDIT_CARD": "[CARD_REDACTED]",
    "INE": "[INE_REDACTED]",
    "PASSPORT": "[PASSPORT_REDACTED]",
    "NSS": "[NSS_REDACTED]",
    "ADDRESS": "[ADDRESS_REDACTED]",
}


def detect_pii(text: str, pii_types: list[PIIType] | None = None) -> dict[PIIType, list[str]]:
    """
    Detect PII in text.

    Args:
        text: Text to scan for PII
        pii_types: List of PII types to detect (None = all types)

    Returns:
        Dictionary mapping PII type to list of detected values
    """
    if not text:
        return {}

    results: dict[PIIType, list[str]] = {}
    types_to_check = pii_types or list(PII_PATTERNS.keys())

    for pii_type in types_to_check:
        if pii_type not in PII_PATTERNS:
            continue

        pattern = PII_PATTERNS[pii_type]
        matches = pattern.findall(text)

        if matches:
            # Handle groups in patterns (some patterns have capture groups)
            cleaned_matches = []
            for match in matches:
                if isinstance(match, tuple):
                    # Pattern has groups, take the first non-empty group
                    for group in match:
                        if group:
                            cleaned_matches.append(group)
                            break
                else:
                    cleaned_matches.append(match)

            if cleaned_matches:
                results[pii_type] = cleaned_matches

    return results


def mask_pii(
    text: str,
    pii_types: list[PIIType] | None = None,
    preserve_partial: bool = False,
) -> str:
    """
    Mask PII in text with redaction placeholders.

    Args:
        text: Text containing PII to mask
        pii_types: List of PII types to mask (None = all types)
        preserve_partial: If True, preserve last 4 characters (e.g., "...1234")

    Returns:
        Text with PII replaced by redaction placeholders
    """
    if not text:
        return text

    masked_text = text
    types_to_mask = pii_types or list(PII_PATTERNS.keys())

    for pii_type in types_to_mask:
        if pii_type not in PII_PATTERNS:
            continue

        pattern = PII_PATTERNS[pii_type]
        mask_template = MASK_TEMPLATES.get(pii_type, "[REDACTED]")

        def replacement(match: re.Match) -> str:
            if preserve_partial:
                original = match.group(0)
                if len(original) > 4:
                    return f"{mask_template[:-1]}...{original[-4:]}]"
            return mask_template

        masked_text = pattern.sub(replacement, masked_text)

    return masked_text


def has_pii(text: str, pii_types: list[PIIType] | None = None) -> bool:
    """
    Check if text contains any PII.

    Args:
        text: Text to check
        pii_types: List of PII types to check (None = all types)

    Returns:
        True if any PII is detected
    """
    detected = detect_pii(text, pii_types)
    return len(detected) > 0


def get_pii_summary(text: str) -> dict[str, int]:
    """
    Get a summary of PII types found in text.

    Args:
        text: Text to analyze

    Returns:
        Dictionary mapping PII type to count of occurrences
    """
    detected = detect_pii(text)
    return {pii_type: len(values) for pii_type, values in detected.items()}
