"""
Payment Agent Tools for AP2 Mandate Validation and Processing

⚠️ MINIMAL IMPORTS FROM PARENT PROJECT ⚠️

These tools implement AP2 protocol validation and payment processing with
zero domain knowledge. They operate purely on mandate structures and external
payment infrastructure APIs.

Tools:
1. validate_hp_chain: Validate Human-Present purchase mandate chain
2. validate_hnp_chain: Validate Human-Not-Present autonomous purchase chain
3. retrieve_payment_credentials: Get tokenized payment methods from external provider
4. process_payment_authorization: Process payment authorization with external processor

Strands Integration:
These functions are decorated with @tool to be used by Strands Agent.
External dependencies (credentials_provider, payment_processor) are injected
via configure_payment_tools() before agent creation.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import os
import json

from strands import tool

from .models import IntentMandate, CartMandate, PaymentMandate, SignatureObject
from .crypto import verify_user_signature, verify_agent_signature


# ============================================================================
# External Service Connectors (Dependency Injection)
# ============================================================================

# These are injected by the parent application before agent creation
_credentials_provider: Optional[Callable[[str], Dict[str, Any]]] = None
_payment_processor: Optional[Callable[[str, int, str, Dict], Dict[str, Any]]] = None


def configure_payment_tools(
    credentials_provider: Callable[[str], Dict[str, Any]],
    payment_processor: Callable[[str, int, str, Dict], Dict[str, Any]]
):
    """
    Configure external service connectors for payment tools.

    This function MUST be called before creating the Payment Agent.
    It maintains isolation by accepting connectors as dependencies rather
    than importing from parent project.

    Args:
        credentials_provider: Function(user_id) -> credentials_result
        payment_processor: Function(token, amount, currency, metadata) -> payment_result
    """
    global _credentials_provider, _payment_processor
    _credentials_provider = credentials_provider
    _payment_processor = payment_processor


# ============================================================================
# HP Chain Validation Tool
# ============================================================================

@tool
def validate_hp_chain(cart_mandate_json: str) -> str:
    """
    Validate Human-Present purchase mandate chain for AP2 compliance.

    HP Flow Requirements:
    - Cart must have user signature
    - Cart total amounts must be internally consistent
    - No Intent signature required (context-only)

    Args:
        cart_mandate_json: CartMandate as JSON string

    Returns:
        JSON string with validation result:
        {"valid": bool, "errors": [...], "cart_total_cents": int, "user_id": str}

    AP2 Compliance:
    Validates user authorized this specific cart without any product knowledge.
    """
    errors = []

    try:
        cart_mandate = json.loads(cart_mandate_json)

        # Parse and validate Cart structure
        cart = CartMandate(**cart_mandate)

        # 1. Verify user signature on Cart
        cart_data_without_sig = cart_mandate.copy()
        cart_data_without_sig.pop("signature", None)

        sig = cart.signature
        timestamp_iso = sig.timestamp if isinstance(sig.timestamp, str) else sig.timestamp.isoformat()
        if not verify_user_signature(
            cart_data_without_sig,
            sig.signature_value,
            sig.signer_identity,
            timestamp_iso
        ):
            errors.append("Cart user signature verification failed")

        # 2. Verify signer is the cart owner
        if sig.signer_identity != cart.user_id:
            errors.append(f"Signature signer {sig.signer_identity} != cart user {cart.user_id}")

        # 3. Pydantic already validated totals consistency via model validators

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "cart_total_cents": cart.total.total_cents,
            "user_id": cart.user_id,
        }

        return json.dumps(result)

    except Exception as e:
        errors.append(f"Cart validation exception: {str(e)}")
        result = {
            "valid": False,
            "errors": errors,
            "cart_total_cents": 0,
            "user_id": "unknown",
        }
        return json.dumps(result)


# ============================================================================
# HNP Chain Validation Tool
# ============================================================================

@tool
def validate_hnp_chain(intent_mandate_json: str, cart_mandate_json: str) -> str:
    """
    Validate Human-Not-Present autonomous purchase mandate chain for AP2 compliance.

    HNP Flow Requirements:
    - Intent must have user signature (pre-authorization)
    - Intent must not be expired
    - Cart must have agent signature (autonomous action)
    - Cart must reference Intent ID
    - Cart total must not exceed Intent max_price constraint
    - Cart delivery must not exceed Intent max_delivery_days constraint

    Args:
        intent_mandate_json: IntentMandate as JSON string
        cart_mandate_json: CartMandate as JSON string

    Returns:
        JSON string with validation result:
        {"valid": bool, "errors": [...], "cart_total_cents": int, "user_id": str, ...}

    AP2 Compliance:
    Validates user pre-authorized purchase and agent acted within constraints.
    """
    errors = []

    try:
        intent_mandate = json.loads(intent_mandate_json)
        cart_mandate = json.loads(cart_mandate_json)

        # Parse and validate structures
        intent = IntentMandate(**intent_mandate)
        cart = CartMandate(**cart_mandate)

        # 1. Verify Intent has user signature (HNP requirement)
        if not intent.signature:
            errors.append("HNP Intent must have user signature")
        else:
            intent_data_without_sig = intent_mandate.copy()
            intent_data_without_sig.pop("signature", None)

            sig = intent.signature
            timestamp_iso = sig.timestamp if isinstance(sig.timestamp, str) else sig.timestamp.isoformat()
            if not verify_user_signature(
                intent_data_without_sig,
                sig.signature_value,
                sig.signer_identity,
                timestamp_iso
            ):
                errors.append("Intent user signature verification failed")

            if sig.signer_identity != intent.user_id:
                errors.append(f"Intent signer {sig.signer_identity} != user {intent.user_id}")

        # 2. Verify Intent not expired
        if intent.expiration and datetime.utcnow() > intent.expiration:
            errors.append(f"Intent expired at {intent.expiration.isoformat()}")

        # 3. Verify Cart has agent signature (HNP autonomous action)
        cart_data_without_sig = cart_mandate.copy()
        cart_data_without_sig.pop("signature", None)

        cart_sig = cart.signature
        cart_timestamp_iso = cart_sig.timestamp if isinstance(cart_sig.timestamp, str) else cart_sig.timestamp.isoformat()
        if not verify_agent_signature(
            cart_data_without_sig,
            cart_sig.signature_value,
            cart_sig.signer_identity,
            cart_timestamp_iso
        ):
            errors.append("Cart agent signature verification failed")

        # 4. Verify Cart references Intent
        if cart.references != intent.mandate_id:
            errors.append(
                f"Cart references {cart.references} but Intent is {intent.mandate_id}"
            )

        # 5. Verify user_id matches across chain
        if intent.user_id != cart.user_id:
            errors.append(
                f"User ID mismatch: Intent {intent.user_id} != Cart {cart.user_id}"
            )

        # 6. Verify constraints not violated
        if intent.constraints:
            # Price constraint
            if intent.constraints.max_price_cents is not None:
                if cart.total.total_cents > intent.constraints.max_price_cents:
                    errors.append(
                        f"Cart total {cart.total.total_cents}¢ exceeds "
                        f"Intent max price {intent.constraints.max_price_cents}¢"
                    )

            # Delivery constraint
            if intent.constraints.max_delivery_days is not None:
                if cart.delivery_estimate_days > intent.constraints.max_delivery_days:
                    errors.append(
                        f"Cart delivery {cart.delivery_estimate_days} days exceeds "
                        f"Intent max delivery {intent.constraints.max_delivery_days} days"
                    )

        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "cart_total_cents": cart.total.total_cents,
            "user_id": cart.user_id,
            "intent_id": intent.mandate_id,
            "cart_id": cart.mandate_id,
        }

        return json.dumps(result)

    except Exception as e:
        errors.append(f"Chain validation exception: {str(e)}")
        result = {
            "valid": False,
            "errors": errors,
            "cart_total_cents": 0,
            "user_id": "unknown",
            "intent_id": "unknown",
            "cart_id": "unknown",
        }
        return json.dumps(result)


# ============================================================================
# Credentials Retrieval Tool
# ============================================================================

@tool
def retrieve_payment_credentials(user_id: str) -> str:
    """
    Retrieve tokenized payment methods from Credentials Provider.

    Args:
        user_id: User identifier

    Returns:
        JSON string with credentials result:
        {"success": bool, "payment_methods": [...], "error": str or null}

    AP2 Compliance:
    Returns only tokenized credentials (tok_* format), never raw card data.
    """
    if not _credentials_provider:
        result = {
            "success": False,
            "payment_methods": [],
            "error": "Credentials Provider not configured. Call configure_payment_tools() first."
        }
        return json.dumps(result)

    try:
        result = _credentials_provider(user_id)
        return json.dumps(result)
    except Exception as e:
        result = {
            "success": False,
            "payment_methods": [],
            "error": f"Failed to retrieve credentials: {str(e)}"
        }
        return json.dumps(result)


# ============================================================================
# Payment Processing Tool
# ============================================================================

@tool
def process_payment_authorization(
    payment_token: str,
    amount_cents: int,
    currency: str,
    metadata_json: str
) -> str:
    """
    Process payment authorization with Payment Processor.

    Args:
        payment_token: Tokenized payment credential
        amount_cents: Transaction amount in cents
        currency: Currency code (e.g., "USD")
        metadata_json: Transaction metadata as JSON string

    Returns:
        JSON string with payment result:
        {"status": str, "authorization_code": str or null, "decline_reason": str or null, ...}

    AP2 Compliance:
    Operates on tokenized credentials only, never sees raw payment data.
    """
    if not _payment_processor:
        result = {
            "success": False,
            "status": "declined",
            "authorization_code": None,
            "decline_reason": None,
            "error": "Payment Processor not configured. Call configure_payment_tools() first."
        }
        return json.dumps(result)

    try:
        metadata = json.loads(metadata_json) if metadata_json else {}
        result = _payment_processor(payment_token, amount_cents, currency, metadata)
        return json.dumps(result)
    except Exception as e:
        result = {
            "success": False,
            "status": "declined",
            "authorization_code": None,
            "decline_reason": None,
            "error": f"Failed to process payment: {str(e)}"
        }
        return json.dumps(result)
