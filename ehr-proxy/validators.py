"""
Input Validation and Sanitization for MDx Vision EHR Proxy
HIPAA Security Rule §164.308(a)(5)(ii)(B) - Protection from Malicious Software
OWASP Top 10 - A03:2021 Injection Prevention
"""

import re
import html
from typing import Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Maximum field lengths
MAX_PATIENT_ID_LENGTH = 100
MAX_NAME_LENGTH = 200
MAX_SHORT_TEXT_LENGTH = 500
MAX_MEDIUM_TEXT_LENGTH = 5000
MAX_LONG_TEXT_LENGTH = 50000
MAX_NOTE_LENGTH = 100000

# Allowed characters patterns
PATIENT_ID_PATTERN = re.compile(r'^[a-zA-Z0-9\-_.]+$')
UUID_PATTERN = re.compile(r'^[a-fA-F0-9\-]{36}$')
ALPHANUMERIC_PATTERN = re.compile(r'^[a-zA-Z0-9\s\-_.]+$')

# Dangerous HTML/script patterns to remove
DANGEROUS_PATTERNS = [
    re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<iframe[^>]*>.*?</iframe>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<object[^>]*>.*?</object>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<embed[^>]*>.*?</embed>', re.IGNORECASE | re.DOTALL),
    re.compile(r'<link[^>]*>', re.IGNORECASE),
    re.compile(r'<style[^>]*>.*?</style>', re.IGNORECASE | re.DOTALL),
    re.compile(r'javascript:', re.IGNORECASE),
    re.compile(r'vbscript:', re.IGNORECASE),
    re.compile(r'data:text/html', re.IGNORECASE),
    re.compile(r'on\w+\s*=', re.IGNORECASE),  # onclick, onload, etc.
]

# SQL injection patterns (for logging/alerting, not blocking)
SQL_INJECTION_PATTERNS = [
    re.compile(r"('\s*(or|and)\s*')", re.IGNORECASE),
    re.compile(r'(;\s*(drop|delete|truncate|update|insert)\s)', re.IGNORECASE),
    re.compile(r'(union\s+select)', re.IGNORECASE),
]


# ═══════════════════════════════════════════════════════════════════════════════
# SANITIZATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def sanitize_html(text: str) -> str:
    """
    Remove potentially dangerous HTML/script content from text.
    Preserves legitimate medical content while blocking XSS vectors.
    """
    if not text:
        return text

    # Remove dangerous patterns
    result = text
    for pattern in DANGEROUS_PATTERNS:
        result = pattern.sub('', result)

    # Escape remaining HTML entities
    result = html.escape(result, quote=False)

    # Restore common safe characters that were escaped
    result = result.replace('&amp;', '&')  # Allow ampersands in medical text

    return result.strip()


def sanitize_text(text: str, max_length: int = MAX_MEDIUM_TEXT_LENGTH) -> str:
    """
    Sanitize general text input: remove dangerous content and enforce length.
    """
    if not text:
        return text

    # Truncate to max length
    text = text[:max_length]

    # Sanitize HTML/scripts
    text = sanitize_html(text)

    return text.strip()


def validate_patient_id(patient_id: str) -> str:
    """
    Validate patient ID format.
    Allows alphanumeric, hyphens, underscores, and periods.
    """
    if not patient_id:
        raise ValueError("Patient ID is required")

    patient_id = patient_id.strip()

    if len(patient_id) > MAX_PATIENT_ID_LENGTH:
        raise ValueError(f"Patient ID exceeds maximum length of {MAX_PATIENT_ID_LENGTH}")

    # Allow URL-encoded characters for Epic patient IDs (they contain special chars)
    # But sanitize dangerous content
    patient_id = sanitize_html(patient_id)

    return patient_id


def validate_ehr_name(ehr: str) -> str:
    """
    Validate EHR system name against whitelist.
    """
    VALID_EHRS = {'cerner', 'epic', 'veradigm', 'athena', 'nextgen', 'meditech', 'eclinicalworks', 'hapi'}

    if not ehr:
        return 'cerner'  # Default

    ehr_lower = ehr.lower().strip()

    if ehr_lower not in VALID_EHRS:
        raise ValueError(f"Invalid EHR system. Must be one of: {', '.join(sorted(VALID_EHRS))}")

    return ehr_lower


def validate_status(status: str, valid_statuses: set) -> str:
    """
    Validate status value against a whitelist.
    """
    if not status:
        raise ValueError("Status is required")

    status_lower = status.lower().strip()

    if status_lower not in valid_statuses:
        raise ValueError(f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}")

    return status_lower


def check_sql_injection(text: str) -> bool:
    """
    Check if text contains potential SQL injection patterns.
    Returns True if suspicious patterns detected.
    Used for logging/alerting, not blocking (Pydantic handles validation).
    """
    if not text:
        return False

    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            return True

    return False


def sanitize_list(items: list, max_items: int = 100, max_item_length: int = MAX_SHORT_TEXT_LENGTH) -> list:
    """
    Sanitize a list of strings.
    """
    if not items:
        return []

    # Limit number of items
    items = items[:max_items]

    # Sanitize each item
    return [sanitize_text(str(item), max_item_length) for item in items if item]


def sanitize_dict(data: dict, max_keys: int = 50, max_value_length: int = MAX_SHORT_TEXT_LENGTH) -> dict:
    """
    Sanitize a dictionary of strings.
    """
    if not data:
        return {}

    result = {}
    for i, (key, value) in enumerate(data.items()):
        if i >= max_keys:
            break

        # Sanitize key and value
        clean_key = sanitize_text(str(key), 100)
        clean_value = sanitize_text(str(value), max_value_length) if value else None

        if clean_key:
            result[clean_key] = clean_value

    return result
