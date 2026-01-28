"""
Error Handling Module (Issue #30)
Sanitizes error messages to prevent leaking internal details.

OWASP: Improper Error Handling - CWE-209, CWE-211
HIPAA: §164.312(a)(1) - Access Control, prevent information disclosure
"""

import uuid
import re
import traceback
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standardized error codes for client responses."""
    # Authentication/Authorization
    AUTH_REQUIRED = "AUTH_001"
    AUTH_INVALID = "AUTH_002"
    AUTH_EXPIRED = "AUTH_003"
    ACCESS_DENIED = "AUTH_004"

    # Resource errors
    NOT_FOUND = "RES_001"
    ALREADY_EXISTS = "RES_002"
    CONFLICT = "RES_003"

    # Validation errors
    INVALID_INPUT = "VAL_001"
    MISSING_FIELD = "VAL_002"
    INVALID_FORMAT = "VAL_003"

    # Rate limiting
    RATE_LIMITED = "RATE_001"

    # External service errors
    EHR_UNAVAILABLE = "EXT_001"
    AI_UNAVAILABLE = "EXT_002"
    TRANSCRIPTION_UNAVAILABLE = "EXT_003"

    # Internal errors
    INTERNAL_ERROR = "INT_001"
    DATABASE_ERROR = "INT_002"
    CONFIG_ERROR = "INT_003"


# Patterns that indicate sensitive information
SENSITIVE_PATTERNS = [
    # File paths
    r'/[a-zA-Z0-9_\-./]+\.(py|java|js|ts|go|rb)',
    r'File "[^"]+", line \d+',
    r'at [a-zA-Z0-9_.]+\([^)]+:\d+\)',

    # Stack traces
    r'Traceback \(most recent call last\)',
    r'^\s+at\s+',
    r'Exception in thread',

    # Database details
    r'(mysql|postgresql|postgres|mongodb|sqlite|redis)://[^\s]+',
    r'connection.*refused',
    r'(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE)\s+',
    r'relation "[^"]+" does not exist',
    r'column "[^"]+" does not exist',

    # API keys and secrets
    r'(api[_-]?key|secret|token|password|auth)["\']?\s*[:=]\s*["\']?[a-zA-Z0-9_\-]+',
    r'sk-[a-zA-Z0-9]+',  # OpenAI keys
    r'Bearer [a-zA-Z0-9\-._~+/]+=*',

    # Internal URLs and ports
    r'localhost:\d+',
    r'127\.0\.0\.1:\d+',
    r'0\.0\.0\.0:\d+',
    r'http://internal[^\s]+',

    # Class/function names (internal)
    r'[A-Z][a-zA-Z]+Exception',
    r'[a-z_]+\.[a-z_]+\([^)]*\)',

    # IP addresses (internal)
    r'\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
    r'\b172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}\b',
    r'\b192\.168\.\d{1,3}\.\d{1,3}\b',
]

# Compiled patterns for efficiency
_compiled_patterns = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in SENSITIVE_PATTERNS]


def generate_correlation_id() -> str:
    """Generate a unique correlation ID for error tracking."""
    return str(uuid.uuid4())[:8].upper()


def contains_sensitive_info(message: str) -> bool:
    """Check if message contains sensitive information."""
    if not message:
        return False
    for pattern in _compiled_patterns:
        if pattern.search(message):
            return True
    return False


def sanitize_error_message(
    message: str,
    allow_field_names: bool = True
) -> str:
    """
    Sanitize an error message by removing sensitive information.

    Args:
        message: The original error message
        allow_field_names: Whether to allow field names in validation errors

    Returns:
        Sanitized message safe for client display
    """
    if not message:
        return "An error occurred"

    # If message contains sensitive info, replace with generic
    if contains_sensitive_info(message):
        return "An error occurred while processing your request"

    # Truncate long messages
    if len(message) > 200:
        message = message[:200] + "..."

    return message


def get_safe_error_response(
    status_code: int,
    original_error: Optional[str] = None,
    error_code: Optional[ErrorCode] = None,
    correlation_id: Optional[str] = None,
    field: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate a safe error response for clients.

    Args:
        status_code: HTTP status code
        original_error: Original error message (will be sanitized)
        error_code: Standardized error code
        correlation_id: Unique ID for tracking
        field: Field name for validation errors

    Returns:
        Safe error response dict
    """
    correlation_id = correlation_id or generate_correlation_id()

    # Default messages by status code
    default_messages = {
        400: "Invalid request",
        401: "Authentication required",
        403: "Access denied",
        404: "Resource not found",
        409: "Resource conflict",
        422: "Validation error",
        429: "Too many requests",
        500: "Internal server error",
        502: "Service temporarily unavailable",
        503: "Service temporarily unavailable",
        504: "Request timeout",
    }

    # Default error codes by status code
    default_codes = {
        400: ErrorCode.INVALID_INPUT,
        401: ErrorCode.AUTH_REQUIRED,
        403: ErrorCode.ACCESS_DENIED,
        404: ErrorCode.NOT_FOUND,
        409: ErrorCode.CONFLICT,
        422: ErrorCode.INVALID_FORMAT,
        429: ErrorCode.RATE_LIMITED,
        500: ErrorCode.INTERNAL_ERROR,
        502: ErrorCode.EHR_UNAVAILABLE,
        503: ErrorCode.EHR_UNAVAILABLE,
        504: ErrorCode.EHR_UNAVAILABLE,
    }

    # Get safe message
    if status_code >= 500:
        # Never expose internal error details for 5xx
        message = default_messages.get(status_code, "An unexpected error occurred")
    elif original_error:
        # Sanitize client errors but allow some detail
        message = sanitize_error_message(original_error)
        if contains_sensitive_info(original_error):
            message = default_messages.get(status_code, "An error occurred")
    else:
        message = default_messages.get(status_code, "An error occurred")

    response = {
        "error": message,
        "code": (error_code or default_codes.get(status_code, ErrorCode.INTERNAL_ERROR)).value,
        "request_id": correlation_id,
    }

    # Add field info for validation errors (if safe)
    if field and status_code in (400, 422) and not contains_sensitive_info(field):
        response["field"] = field

    return response


def log_error_with_context(
    error: Exception,
    correlation_id: str,
    context: Optional[Dict[str, Any]] = None,
    level: str = "error"
) -> None:
    """
    Log full error details server-side with correlation ID.

    This logs the complete error for debugging while only
    returning sanitized info to clients.
    """
    log_data = {
        "correlation_id": correlation_id,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": traceback.format_exc(),
    }

    if context:
        # Sanitize context before logging (remove actual secrets)
        safe_context = {}
        for key, value in context.items():
            if any(s in key.lower() for s in ['password', 'secret', 'token', 'key', 'auth']):
                safe_context[key] = "[REDACTED]"
            else:
                safe_context[key] = value
        log_data["context"] = safe_context

    log_func = getattr(logger, level, logger.error)
    log_func(f"Error [{correlation_id}]: {type(error).__name__}", extra=log_data)


# Safe messages for common third-party service errors
THIRD_PARTY_ERROR_MESSAGES = {
    # EHR errors
    "cerner": "EHR service is temporarily unavailable",
    "epic": "EHR service is temporarily unavailable",
    "fhir": "EHR service is temporarily unavailable",
    "veradigm": "EHR service is temporarily unavailable",

    # AI service errors
    "openai": "AI service is temporarily unavailable",
    "anthropic": "AI service is temporarily unavailable",
    "claude": "AI service is temporarily unavailable",

    # Transcription errors
    "assemblyai": "Transcription service is temporarily unavailable",
    "deepgram": "Transcription service is temporarily unavailable",

    # Generic external
    "timeout": "The request timed out. Please try again.",
    "connection": "Unable to connect to external service",
}


def get_safe_third_party_error(error: Exception, service_hint: Optional[str] = None) -> str:
    """
    Get a safe error message for third-party service failures.

    Args:
        error: The original exception
        service_hint: Optional hint about which service failed

    Returns:
        Safe generic message for the client
    """
    error_str = str(error).lower()

    # Check for service-specific errors
    for service, message in THIRD_PARTY_ERROR_MESSAGES.items():
        if service in error_str or (service_hint and service in service_hint.lower()):
            return message

    # Check for timeout/connection errors
    if "timeout" in error_str:
        return THIRD_PARTY_ERROR_MESSAGES["timeout"]
    if "connection" in error_str or "connect" in error_str:
        return THIRD_PARTY_ERROR_MESSAGES["connection"]

    # Generic fallback
    return "An external service is temporarily unavailable"


class SanitizedHTTPException(Exception):
    """
    Custom exception that ensures error messages are sanitized.

    Use this instead of HTTPException when you want automatic sanitization.
    """
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[ErrorCode] = None,
        internal_message: Optional[str] = None
    ):
        self.status_code = status_code
        self.detail = sanitize_error_message(detail)
        self.error_code = error_code
        self.internal_message = internal_message  # For logging only
        super().__init__(self.detail)
