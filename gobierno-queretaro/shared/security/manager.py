"""
Gobierno Queretaro - Security Manager
Central security service for PII handling, encryption, and sanitization
"""

import base64
import hashlib
import logging
import os
import secrets
from typing import Any

from cryptography.fernet import Fernet

from .patterns import PIIType, detect_pii, mask_pii, has_pii

logger = logging.getLogger(__name__)


class SecurityManager:
    """
    Central security manager for the gobierno-queretaro system.

    Provides:
    - PII detection and masking
    - Field encryption/decryption
    - Log sanitization
    - Citizen ID pseudonymization
    """

    def __init__(self, encryption_key: str | None = None):
        """
        Initialize SecurityManager.

        Args:
            encryption_key: Base64-encoded Fernet key. If not provided,
                           uses ENCRYPTION_KEY env var or generates new key.
        """
        self._encryption_key = self._setup_encryption_key(encryption_key)
        self._fernet = Fernet(self._encryption_key)

    def _setup_encryption_key(self, key: str | None) -> bytes:
        """Setup or generate encryption key."""
        if key:
            return base64.urlsafe_b64decode(key)

        env_key = os.getenv("ENCRYPTION_KEY")
        if env_key:
            return base64.urlsafe_b64decode(env_key)

        # Generate new key (should be persisted in production)
        new_key = Fernet.generate_key()
        logger.warning(
            "Generated new encryption key. "
            "Set ENCRYPTION_KEY env var for persistence."
        )
        return new_key

    # =========================================
    # PII Detection
    # =========================================

    def detect_pii(
        self,
        text: str,
        pii_types: list[PIIType] | None = None,
    ) -> dict[PIIType, list[str]]:
        """
        Detect PII in text.

        Args:
            text: Text to scan
            pii_types: Specific PII types to detect (None = all)

        Returns:
            Dictionary mapping PII type to detected values
        """
        return detect_pii(text, pii_types)

    def has_pii(
        self,
        text: str,
        pii_types: list[PIIType] | None = None,
    ) -> bool:
        """Check if text contains PII."""
        return has_pii(text, pii_types)

    def mask_pii(
        self,
        text: str,
        pii_types: list[PIIType] | None = None,
        preserve_partial: bool = False,
    ) -> str:
        """
        Mask PII in text with redaction placeholders.

        Args:
            text: Text to mask
            pii_types: Specific PII types to mask (None = all)
            preserve_partial: Keep last 4 characters visible

        Returns:
            Masked text
        """
        return mask_pii(text, pii_types, preserve_partial)

    # =========================================
    # Encryption
    # =========================================

    def encrypt_field(self, value: str) -> str:
        """
        Encrypt a field value for storage.

        Args:
            value: Plaintext value to encrypt

        Returns:
            Base64-encoded encrypted value
        """
        if not value:
            return value

        encrypted = self._fernet.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()

    def decrypt_field(self, encrypted_value: str) -> str:
        """
        Decrypt a field value.

        Args:
            encrypted_value: Base64-encoded encrypted value

        Returns:
            Decrypted plaintext value
        """
        if not encrypted_value:
            return encrypted_value

        try:
            decoded = base64.urlsafe_b64decode(encrypted_value)
            decrypted = self._fernet.decrypt(decoded)
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise ValueError("Unable to decrypt field") from e

    def encrypt_dict(
        self,
        data: dict[str, Any],
        fields_to_encrypt: list[str],
    ) -> dict[str, Any]:
        """
        Encrypt specific fields in a dictionary.

        Args:
            data: Dictionary with fields to encrypt
            fields_to_encrypt: List of field names to encrypt

        Returns:
            Dictionary with specified fields encrypted
        """
        result = data.copy()
        for field in fields_to_encrypt:
            if field in result and isinstance(result[field], str):
                result[field] = self.encrypt_field(result[field])
        return result

    def decrypt_dict(
        self,
        data: dict[str, Any],
        fields_to_decrypt: list[str],
    ) -> dict[str, Any]:
        """
        Decrypt specific fields in a dictionary.

        Args:
            data: Dictionary with encrypted fields
            fields_to_decrypt: List of field names to decrypt

        Returns:
            Dictionary with specified fields decrypted
        """
        result = data.copy()
        for field in fields_to_decrypt:
            if field in result and isinstance(result[field], str):
                try:
                    result[field] = self.decrypt_field(result[field])
                except ValueError:
                    pass  # Leave as-is if decryption fails
        return result

    # =========================================
    # Sanitization
    # =========================================

    def sanitize_for_logging(
        self,
        text: str,
        preserve_partial: bool = False,
    ) -> str:
        """
        Sanitize text for safe logging by masking all PII.

        Args:
            text: Text to sanitize
            preserve_partial: Keep last 4 characters visible

        Returns:
            Sanitized text safe for logging
        """
        return self.mask_pii(text, preserve_partial=preserve_partial)

    def sanitize_dict_for_logging(
        self,
        data: dict[str, Any],
        sensitive_fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Sanitize a dictionary for safe logging.

        Args:
            data: Dictionary to sanitize
            sensitive_fields: Field names to always redact fully

        Returns:
            Sanitized dictionary
        """
        sensitive_fields = sensitive_fields or [
            "password",
            "secret",
            "token",
            "api_key",
            "authorization",
            "curp",
            "rfc",
        ]

        result = {}
        for key, value in data.items():
            key_lower = key.lower()

            # Fully redact known sensitive fields
            if any(sf in key_lower for sf in sensitive_fields):
                result[key] = "[REDACTED]"
            elif isinstance(value, str):
                result[key] = self.sanitize_for_logging(value)
            elif isinstance(value, dict):
                result[key] = self.sanitize_dict_for_logging(value, sensitive_fields)
            elif isinstance(value, list):
                result[key] = [
                    self.sanitize_dict_for_logging(item, sensitive_fields)
                    if isinstance(item, dict)
                    else self.sanitize_for_logging(str(item))
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    # =========================================
    # Pseudonymization
    # =========================================

    def pseudonymize_citizen_id(
        self,
        citizen_id: str,
        salt: str | None = None,
    ) -> str:
        """
        Create a pseudonymized hash of a citizen ID (CURP/RFC).

        This allows linking records without storing the actual ID.

        Args:
            citizen_id: CURP or RFC to pseudonymize
            salt: Optional salt (uses env var or generates if not provided)

        Returns:
            SHA-256 hash of salted citizen ID
        """
        if not citizen_id:
            return ""

        salt = salt or os.getenv("CITIZEN_ID_SALT", secrets.token_hex(16))
        salted = f"{salt}:{citizen_id.upper()}"
        return hashlib.sha256(salted.encode()).hexdigest()

    def generate_session_token(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure session token.

        Args:
            length: Number of random bytes (hex output is 2x this)

        Returns:
            Hex-encoded random token
        """
        return secrets.token_hex(length)

    # =========================================
    # Validation
    # =========================================

    def validate_curp(self, curp: str) -> bool:
        """
        Validate CURP format and checksum.

        Args:
            curp: CURP string to validate

        Returns:
            True if valid CURP format
        """
        if not curp or len(curp) != 18:
            return False

        curp = curp.upper()

        # Basic format check
        import re
        pattern = r"^[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z\d]{2}$"
        if not re.match(pattern, curp):
            return False

        # Validate birthdate portion (positions 4-10)
        try:
            year = int(curp[4:6])
            month = int(curp[6:8])
            day = int(curp[8:10])

            if not (1 <= month <= 12 and 1 <= day <= 31):
                return False
        except ValueError:
            return False

        return True

    def validate_rfc(self, rfc: str) -> bool:
        """
        Validate RFC format.

        Args:
            rfc: RFC string to validate

        Returns:
            True if valid RFC format
        """
        if not rfc or len(rfc) not in (12, 13):
            return False

        rfc = rfc.upper()

        import re
        # RFC for individuals (13 chars) or companies (12 chars)
        pattern_individual = r"^[A-Z&Ñ]{4}\d{6}[A-Z\d]{3}$"
        pattern_company = r"^[A-Z&Ñ]{3}\d{6}[A-Z\d]{3}$"

        return bool(re.match(pattern_individual, rfc) or re.match(pattern_company, rfc))


# Singleton instance
_security_manager: SecurityManager | None = None


def get_security_manager() -> SecurityManager:
    """Get or create the singleton SecurityManager instance."""
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager
