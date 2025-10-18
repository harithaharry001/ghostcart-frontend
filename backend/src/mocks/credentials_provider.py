"""
Mock Credentials Provider

Simulates tokenized payment method retrieval for AP2 demonstration.
Returns 2-3 payment methods per user with tokenized credentials.

AP2 Compliance: Credentials Provider role per AP2 specification - provides
tokenized payment methods, never exposes raw card data.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PaymentMethod:
    """Tokenized payment method data structure."""
    token: str
    type: str  # "visa", "mastercard", "amex"
    last_four: str
    expiry_month: int
    expiry_year: int
    cardholder_name: str
    billing_zip: str
    is_default: bool


# User payment method registry - maps user_id to available payment methods
USER_PAYMENT_METHODS: Dict[str, List[PaymentMethod]] = {
    "user_demo_001": [
        PaymentMethod(
            token="tok_visa_4242",
            type="visa",
            last_four="4242",
            expiry_month=12,
            expiry_year=2027,
            cardholder_name="Jane Smith",
            billing_zip="94102",
            is_default=True
        ),
        PaymentMethod(
            token="tok_mc_5555",
            type="mastercard",
            last_four="5555",
            expiry_month=8,
            expiry_year=2026,
            cardholder_name="Jane Smith",
            billing_zip="94102",
            is_default=False
        ),
    ],
    "user_demo_002": [
        PaymentMethod(
            token="tok_amex_3782",
            type="amex",
            last_four="3782",
            expiry_month=3,
            expiry_year=2028,
            cardholder_name="Alex Johnson",
            billing_zip="10001",
            is_default=True
        ),
        PaymentMethod(
            token="tok_visa_1111",
            type="visa",
            last_four="1111",
            expiry_month=6,
            expiry_year=2025,
            cardholder_name="Alex Johnson",
            billing_zip="10001",
            is_default=False
        ),
        PaymentMethod(
            token="tok_mc_7777",
            type="mastercard",
            last_four="7777",
            expiry_month=11,
            expiry_year=2027,
            cardholder_name="Alex Johnson",
            billing_zip="10001",
            is_default=False
        ),
    ],
    "user_demo_003": [
        PaymentMethod(
            token="tok_visa_9999",
            type="visa",
            last_four="9999",
            expiry_month=4,
            expiry_year=2026,
            cardholder_name="Chris Lee",
            billing_zip="60601",
            is_default=True
        ),
    ],
}


def get_payment_methods(user_id: str) -> List[Dict[str, Any]]:
    """
    Retrieve tokenized payment methods for a user.

    Args:
        user_id: User identifier

    Returns:
        List of tokenized payment methods with metadata

    Raises:
        ValueError: If user has no payment methods configured

    AP2 Compliance:
    - Returns only tokenized credentials (tok_* format)
    - Never exposes raw card numbers or CVV
    - Provides metadata needed for payment processing
    """
    payment_methods = USER_PAYMENT_METHODS.get(user_id, [])

    if not payment_methods:
        raise ValueError(f"No payment methods available for user {user_id}")

    return [
        {
            "token": pm.token,
            "type": pm.type,
            "last_four": pm.last_four,
            "expiry_month": pm.expiry_month,
            "expiry_year": pm.expiry_year,
            "cardholder_name": pm.cardholder_name,
            "billing_zip": pm.billing_zip,
            "is_default": pm.is_default,
        }
        for pm in payment_methods
    ]


def get_default_payment_method(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user's default payment method.

    Args:
        user_id: User identifier

    Returns:
        Default payment method dict, or None if no default set

    AP2 Compliance: Provides default method for autonomous agent use.
    """
    payment_methods = USER_PAYMENT_METHODS.get(user_id, [])

    for pm in payment_methods:
        if pm.is_default:
            return {
                "token": pm.token,
                "type": pm.type,
                "last_four": pm.last_four,
                "expiry_month": pm.expiry_month,
                "expiry_year": pm.expiry_year,
                "cardholder_name": pm.cardholder_name,
                "billing_zip": pm.billing_zip,
                "is_default": pm.is_default,
            }

    return None


def validate_payment_token(token: str) -> bool:
    """
    Check if payment token exists in system.

    Args:
        token: Payment token to validate

    Returns:
        True if token exists, False otherwise

    AP2 Compliance: Used by Payment Agent to validate credentials before processing.
    """
    for user_methods in USER_PAYMENT_METHODS.values():
        for pm in user_methods:
            if pm.token == token:
                return True
    return False
