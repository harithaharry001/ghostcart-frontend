"""
Mock Payment Processor

Simulates payment authorization for AP2 demonstration.
~90% approval rate with deterministic test scenarios.

AP2 Compliance: Payment Processor role per AP2 specification - processes
payments using tokenized credentials, never accesses product/merchant data.
"""
import hashlib
from typing import Dict, Any, Literal
from datetime import datetime


# Test tokens that trigger specific behaviors
DECLINE_TOKENS = {
    "tok_decline": "insufficient_funds",
    "tok_decline_fraud": "fraud_suspected",
    "tok_decline_expired": "card_expired",
    "tok_decline_invalid": "invalid_card",
}


def authorize_payment(
    payment_token: str,
    amount_cents: int,
    currency: str = "USD",
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Process payment authorization using tokenized credentials.

    Args:
        payment_token: Tokenized payment credential (tok_*)
        amount_cents: Transaction amount in cents
        currency: Currency code (default USD)
        metadata: Optional transaction metadata (transaction_id, user_id, etc.)

    Returns:
        Authorization result dictionary with status and details:
        - status: "authorized" or "declined"
        - authorization_code: Unique auth code if approved (auth_*)
        - decline_reason: Reason if declined
        - processed_at: Timestamp of processing
        - amount_cents: Confirmed amount
        - currency: Confirmed currency

    AP2 Compliance:
    - Processor operates on tokens only (no raw card data)
    - Never accesses product details or merchant information
    - Provides authorization codes for successful transactions
    - Returns standardized decline reasons

    Mock Behavior:
    - Special tokens (tok_decline*) trigger specific decline scenarios
    - Other tokens have ~90% approval rate based on deterministic hash
    """
    from ..config import settings

    metadata = metadata or {}
    processed_at = datetime.utcnow()

    # Demo mode: Always approve for demonstration
    if settings.demo_mode:
        should_approve = True
    else:
        # Check for special decline test tokens
        if payment_token in DECLINE_TOKENS:
            return {
                "status": "declined",
                "authorization_code": None,
                "decline_reason": DECLINE_TOKENS[payment_token],
                "processed_at": processed_at.isoformat(),
                "amount_cents": amount_cents,
                "currency": currency,
                "metadata": metadata,
            }

        # Deterministic approval/decline based on token + amount hash
        # This gives ~90% approval rate
        hash_input = f"{payment_token}:{amount_cents}:{currency}"
        hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest()[:8], 16)
        should_approve = (hash_value % 10) != 0  # 90% approval (0-9, decline only on 0)

    if should_approve:
        # Generate authorization code from hash
        auth_code = f"auth_{hashlib.sha256(f'{payment_token}:{processed_at.isoformat()}'.encode()).hexdigest()[:12]}"

        return {
            "status": "authorized",
            "authorization_code": auth_code,
            "decline_reason": None,
            "processed_at": processed_at.isoformat(),
            "amount_cents": amount_cents,
            "currency": currency,
            "metadata": metadata,
        }
    else:
        # Random decline reason for the ~10% that fail
        decline_reasons = ["insufficient_funds", "do_not_honor", "generic_decline"]
        reason_index = hash_value % len(decline_reasons)

        return {
            "status": "declined",
            "authorization_code": None,
            "decline_reason": decline_reasons[reason_index],
            "processed_at": processed_at.isoformat(),
            "amount_cents": amount_cents,
            "currency": currency,
            "metadata": metadata,
        }


def void_authorization(authorization_code: str) -> Dict[str, Any]:
    """
    Void a previously authorized payment.

    Args:
        authorization_code: Authorization code to void

    Returns:
        Void confirmation with timestamp

    AP2 Compliance: Allows cancellation of authorized but not captured payments.

    Mock Behavior: Always succeeds for demo purposes.
    """
    return {
        "status": "voided",
        "authorization_code": authorization_code,
        "voided_at": datetime.utcnow().isoformat(),
    }


def get_processor_status() -> Dict[str, Any]:
    """
    Check payment processor availability.

    Returns:
        Processor status and capabilities

    AP2 Compliance: Allows health checking before payment attempts.

    Mock Behavior: Always returns operational.
    """
    return {
        "status": "operational",
        "supported_currencies": ["USD"],
        "supported_card_types": ["visa", "mastercard", "amex"],
        "max_amount_cents": 100000000,  # $1M max
        "min_amount_cents": 50,  # $0.50 min
    }
