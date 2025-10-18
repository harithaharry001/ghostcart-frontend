"""
AP2 Exception Hierarchy

Standard error codes per AP2 specification for interoperability.
All errors use ap2: prefix for protocol compliance.
"""
from typing import Optional, Dict, Any


class AP2Error(Exception):
    """
    Base exception for all AP2 protocol errors.

    AP2 Compliance: All errors must use standardized error codes
    from the official specification for interoperability.
    """

    def __init__(
        self,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to API error response format."""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ChainInvalidError(AP2Error):
    """
    Mandate chain validation failed.

    Examples:
    - Cart does not reference Intent in HNP flow
    - Missing mandate in chain
    - Chain breaks AP2 linking requirements
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("ap2:mandate:chain_invalid", message, details)


class SignatureInvalidError(AP2Error):
    """
    Signature verification failed.

    Examples:
    - HMAC verification failed
    - Signer identity mismatch
    - Signature does not match mandate content
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("ap2:mandate:signature_invalid", message, details)


class ExpiredError(AP2Error):
    """
    Mandate past expiration time.

    Example:
    - Current timestamp > Intent expiration timestamp
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("ap2:mandate:expired", message, details)


class ConstraintsViolatedError(AP2Error):
    """
    Constraint validation failed.

    Examples:
    - Cart total exceeds Intent max_price
    - Delivery time exceeds Intent max_delivery_days
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("ap2:mandate:constraints_violated", message, details)


class CredentialsUnavailableError(AP2Error):
    """
    Payment credentials not accessible.

    Example:
    - Credentials Provider returned no payment methods for user
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("ap2:credentials:unavailable", message, details)


class PaymentDeclinedError(AP2Error):
    """
    Payment processor declined transaction.

    Examples:
    - Insufficient funds
    - Card expired
    - Fraud suspected
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__("ap2:payment:declined", message, details)
