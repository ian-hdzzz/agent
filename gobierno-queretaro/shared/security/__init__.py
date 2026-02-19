"""
Gobierno Queretaro - Security Module
PII detection, masking, encryption, and audit logging
"""

from .manager import SecurityManager, get_security_manager
from .patterns import PII_PATTERNS, PIIType, detect_pii, mask_pii, has_pii
from .audit import AuditLogger, AuditEvent, AuditEventType, get_audit_logger

__all__ = [
    "SecurityManager",
    "get_security_manager",
    "PII_PATTERNS",
    "PIIType",
    "detect_pii",
    "mask_pii",
    "has_pii",
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "get_audit_logger",
]
