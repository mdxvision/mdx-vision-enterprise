"""
Structured Logging with Correlation IDs (Issue #90)

Provides JSON-formatted logging with automatic correlation ID propagation
for distributed tracing across ehr-proxy, backend, and ai-service.

Features:
- JSON structured logging for log aggregation
- Correlation ID extraction from headers (X-B3-TraceId, X-Correlation-ID, X-Request-ID)
- Context propagation (session_id, clinician_id, patient_id, ehr_system)
- Request/response logging middleware
- Configurable log levels via environment variables

Usage:
    from structured_logging import get_logger, log_context

    logger = get_logger(__name__)

    with log_context(session_id="sess_123", patient_id="12724066"):
        logger.info("Processing patient request")
"""

import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Any, Dict, Optional

from pythonjsonlogger import jsonlogger

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT VARIABLES
# ═══════════════════════════════════════════════════════════════════════════════

# Correlation ID for distributed tracing
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)

# Request context
session_id_var: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
clinician_id_var: ContextVar[Optional[str]] = ContextVar('clinician_id', default=None)
patient_id_var: ContextVar[Optional[str]] = ContextVar('patient_id', default=None)
ehr_system_var: ContextVar[Optional[str]] = ContextVar('ehr_system', default=None)

# ═══════════════════════════════════════════════════════════════════════════════
# CUSTOM JSON FORMATTER
# ═══════════════════════════════════════════════════════════════════════════════

class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that includes correlation ID and context in all log entries.
    """

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        super().add_fields(log_record, record, message_dict)

        # Rename standard fields
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name

        # Remove redundant fields
        for field in ['asctime', 'levelname', 'name']:
            log_record.pop(field, None)

        # Add correlation ID
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_record['correlation_id'] = correlation_id

        # Add context from context variables
        session_id = session_id_var.get()
        if session_id:
            log_record['session_id'] = session_id

        clinician_id = clinician_id_var.get()
        if clinician_id:
            log_record['clinician_id'] = clinician_id

        patient_id = patient_id_var.get()
        if patient_id:
            log_record['patient_id'] = patient_id

        ehr_system = ehr_system_var.get()
        if ehr_system:
            log_record['ehr_system'] = ehr_system

        # Add service identifier
        log_record['service'] = 'ehr-proxy'

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

_configured = False

def configure_logging(
    level: Optional[str] = None,
    json_output: bool = True
) -> None:
    """
    Configure structured logging for the application.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
               Defaults to LOG_LEVEL env var or INFO
        json_output: If True, output JSON; if False, output human-readable format
    """
    global _configured

    if _configured:
        return

    # Get log level from environment or parameter
    log_level = level or os.getenv('LOG_LEVEL', 'INFO').upper()

    # Get output format from environment
    use_json = os.getenv('LOG_FORMAT', 'json').lower() == 'json' if json_output else False

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Remove existing handlers
    root_logger.handlers = []

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    if use_json:
        # JSON formatter for production
        formatter = StructuredJsonFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s'
        )
    else:
        # Human-readable formatter for development
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s - %(message)s'
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('chromadb').setLevel(logging.WARNING)
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)

    _configured = True

# ═══════════════════════════════════════════════════════════════════════════════
# LOGGER FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    configure_logging()
    return logging.getLogger(name)

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class log_context:
    """
    Context manager for setting logging context variables.

    Usage:
        with log_context(session_id="sess_123", patient_id="12724066"):
            logger.info("Processing request")  # Automatically includes context
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        clinician_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        ehr_system: Optional[str] = None
    ):
        self.correlation_id = correlation_id
        self.session_id = session_id
        self.clinician_id = clinician_id
        self.patient_id = patient_id
        self.ehr_system = ehr_system
        self._tokens = []

    def __enter__(self):
        if self.correlation_id:
            self._tokens.append(('correlation_id', correlation_id_var.set(self.correlation_id)))
        if self.session_id:
            self._tokens.append(('session_id', session_id_var.set(self.session_id)))
        if self.clinician_id:
            self._tokens.append(('clinician_id', clinician_id_var.set(self.clinician_id)))
        if self.patient_id:
            self._tokens.append(('patient_id', patient_id_var.set(self.patient_id)))
        if self.ehr_system:
            self._tokens.append(('ehr_system', ehr_system_var.set(self.ehr_system)))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        for var_name, token in self._tokens:
            if var_name == 'correlation_id':
                correlation_id_var.reset(token)
            elif var_name == 'session_id':
                session_id_var.reset(token)
            elif var_name == 'clinician_id':
                clinician_id_var.reset(token)
            elif var_name == 'patient_id':
                patient_id_var.reset(token)
            elif var_name == 'ehr_system':
                ehr_system_var.reset(token)
        return False

# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())

def get_correlation_id() -> Optional[str]:
    """Get the current correlation ID."""
    return correlation_id_var.get()

def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)

def set_context(
    session_id: Optional[str] = None,
    clinician_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    ehr_system: Optional[str] = None
) -> None:
    """
    Set logging context variables directly.

    Args:
        session_id: Current session ID
        clinician_id: Current clinician ID (from X-Clinician-Id header)
        patient_id: Current patient ID
        ehr_system: Current EHR system (cerner, epic, etc.)
    """
    if session_id:
        session_id_var.set(session_id)
    if clinician_id:
        clinician_id_var.set(clinician_id)
    if patient_id:
        patient_id_var.set(patient_id)
    if ehr_system:
        ehr_system_var.set(ehr_system)

def clear_context() -> None:
    """Clear all logging context variables."""
    correlation_id_var.set(None)
    session_id_var.set(None)
    clinician_id_var.set(None)
    patient_id_var.set(None)
    ehr_system_var.set(None)

# ═══════════════════════════════════════════════════════════════════════════════
# FASTAPI MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

def create_correlation_middleware():
    """
    Create FastAPI middleware for correlation ID handling.

    Returns:
        Middleware function for FastAPI

    Usage:
        from structured_logging import create_correlation_middleware

        app = FastAPI()
        app.middleware("http")(create_correlation_middleware())
    """
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    import time

    logger = get_logger('ehr-proxy.middleware')

    async def correlation_middleware(request: Request, call_next):
        # Extract correlation ID from headers (in order of preference)
        correlation_id = (
            request.headers.get('X-B3-TraceId') or
            request.headers.get('X-Correlation-ID') or
            request.headers.get('X-Request-ID') or
            generate_correlation_id()
        )

        # Extract context from headers
        clinician_id = request.headers.get('X-Clinician-Id')
        session_id = request.headers.get('X-Session-Id')

        # Set context variables
        correlation_id_var.set(correlation_id)
        if clinician_id:
            clinician_id_var.set(clinician_id)
        if session_id:
            session_id_var.set(session_id)

        # Log request
        start_time = time.time()
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'http_method': request.method,
                'http_path': request.url.path,
                'http_query': str(request.query_params) if request.query_params else None,
                'client_ip': request.client.host if request.client else None
            }
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Request completed: {request.method} {request.url.path} -> {response.status_code}",
                extra={
                    'http_method': request.method,
                    'http_path': request.url.path,
                    'http_status': response.status_code,
                    'duration_ms': round(duration_ms, 2)
                }
            )

            # Add correlation ID to response headers
            response.headers['X-Correlation-ID'] = correlation_id

            return response

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                f"Request failed: {request.method} {request.url.path} - {str(e)}",
                extra={
                    'http_method': request.method,
                    'http_path': request.url.path,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'duration_ms': round(duration_ms, 2)
                },
                exc_info=True
            )
            raise
        finally:
            # Clear context after request
            clear_context()

    return correlation_middleware

# ═══════════════════════════════════════════════════════════════════════════════
# OUTBOUND REQUEST HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def get_correlation_headers() -> Dict[str, str]:
    """
    Get headers to propagate correlation ID to outbound requests.

    Returns:
        Dict with correlation headers to include in outbound HTTP requests

    Usage:
        headers = get_correlation_headers()
        response = await httpx.get(url, headers=headers)
    """
    headers = {}

    correlation_id = correlation_id_var.get()
    if correlation_id:
        headers['X-Correlation-ID'] = correlation_id
        headers['X-B3-TraceId'] = correlation_id  # For Spring Cloud Sleuth compatibility

    session_id = session_id_var.get()
    if session_id:
        headers['X-Session-Id'] = session_id

    clinician_id = clinician_id_var.get()
    if clinician_id:
        headers['X-Clinician-Id'] = clinician_id

    return headers
