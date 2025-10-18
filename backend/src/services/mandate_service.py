"""
Mandate Service

Creates, signs, stores, and retrieves AP2 mandates with database persistence.

AP2 Compliance:
- Intent: Context-only (HP) or pre-authorization (HNP)
- Cart: User-signed (HP) or agent-signed (HNP)
- Payment: Always agent-signed
- All mandates persisted with signatures for audit trail
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..db.models import MandateModel
from ..models.mandates import IntentMandate, CartMandate, PaymentMandate
from ..services.signature_service import (
    sign_user_mandate,
    sign_agent_mandate,
    sign_payment_mandate,
    verify_user_signature,
    verify_agent_signature,
    verify_payment_signature
)

logger = logging.getLogger(__name__)


# ============================================================================
# Intent Mandate Creation
# ============================================================================

async def create_intent_mandate(
    db: AsyncSession,
    user_id: str,
    scenario: str,  # "human_present" or "human_not_present"
    product_query: str,
    constraints: Optional[Dict[str, Any]] = None,
    expiration: Optional[datetime] = None,
    signature_required: bool = False
) -> IntentMandate:
    """
    Create and store Intent mandate.

    Args:
        db: Database session
        user_id: User identifier
        scenario: "human_present" or "human_not_present"
        product_query: What user wants to buy
        constraints: Optional constraints (HNP only)
        expiration: Optional expiration (HNP only)
        signature_required: True for HNP, False for HP

    Returns:
        Created IntentMandate

    AP2 Compliance:
    - HP: Unsigned context-only Intent
    - HNP: User-signed Intent with constraints and expiration
    """
    # Generate mandate ID
    scenario_prefix = "hnp" if scenario == "human_not_present" else "hp"
    mandate_id = f"intent_{scenario_prefix}_{uuid.uuid4().hex[:16]}"

    # Build mandate data
    mandate_data = {
        "mandate_id": mandate_id,
        "mandate_type": "intent",
        "user_id": user_id,
        "scenario": scenario,
        "product_query": product_query,
        "constraints": constraints,
        "expiration": expiration.isoformat() if expiration else None,
    }

    # Sign if required (HNP)
    signature_obj = None
    validation_status = "unsigned" if not signature_required else "valid"
    signer_identity = user_id

    if signature_required:
        signature_obj = sign_user_mandate(mandate_data, user_id)
        mandate_data["signature"] = {
            "algorithm": signature_obj.algorithm,
            "signer_identity": signature_obj.signer_identity,
            "timestamp": signature_obj.timestamp.isoformat(),
            "signature_value": signature_obj.signature_value
        }

    # Validate with Pydantic
    intent_mandate = IntentMandate(**mandate_data)

    # Store in database
    db_mandate = MandateModel(
        id=mandate_id,
        mandate_type="intent",
        user_id=user_id,
        transaction_id=None,
        mandate_data=json.dumps(mandate_data),
        signer_identity=signer_identity,
        signature=signature_obj.signature_value if signature_obj else None,
        signature_metadata=json.dumps({
            "algorithm": signature_obj.algorithm if signature_obj else None,
            "timestamp": signature_obj.timestamp.isoformat() if signature_obj else None
        }) if signature_obj else None,
        validation_status=validation_status,
    )

    db.add(db_mandate)
    await db.commit()
    await db.refresh(db_mandate)

    logger.info(f"Created Intent mandate: {mandate_id}, scenario={scenario}, signed={signature_required}")

    return intent_mandate


# ============================================================================
# Cart Mandate Creation
# ============================================================================

async def create_cart_mandate(
    db: AsyncSession,
    user_id: str,
    items: List[Dict[str, Any]],
    total: Dict[str, Any],
    merchant_info: Dict[str, Any],
    delivery_estimate_days: int,
    intent_reference: Optional[str] = None,
    signed_by: str = "user",  # "user" (HP) or "agent" (HNP)
    signer_id: Optional[str] = None
) -> CartMandate:
    """
    Create and store Cart mandate.

    Args:
        db: Database session
        user_id: User identifier
        items: Line items list
        total: Total breakdown dict
        merchant_info: Merchant info dict
        delivery_estimate_days: Delivery estimate
        intent_reference: Intent ID (optional for HP, required for HNP)
        signed_by: "user" (HP) or "agent" (HNP)
        signer_id: Signer identifier (defaults to user_id for user, "agent" for agent)

    Returns:
        Created CartMandate

    AP2 Compliance:
    - HP: User-signed Cart (immediate purchase authorization)
    - HNP: Agent-signed Cart (autonomous action with Intent reference)
    """
    # Determine scenario from Intent reference pattern
    scenario_prefix = "hp"
    if intent_reference and "hnp" in intent_reference:
        scenario_prefix = "hnp"

    # Generate mandate ID
    mandate_id = f"cart_{scenario_prefix}_{uuid.uuid4().hex[:16]}"

    # Build mandate data without signature
    mandate_data = {
        "mandate_id": mandate_id,
        "mandate_type": "cart",
        "user_id": user_id,
        "items": items,
        "total": total,
        "merchant_info": merchant_info,
        "delivery_estimate_days": delivery_estimate_days,
        "references": intent_reference,
    }

    # Sign Cart
    signer_identity = signer_id or (user_id if signed_by == "user" else "shopping_agent")

    if signed_by == "user":
        signature_obj = sign_user_mandate(mandate_data, signer_identity)
    else:  # agent
        signature_obj = sign_agent_mandate(mandate_data, signer_identity)

    mandate_data["signature"] = {
        "algorithm": signature_obj.algorithm,
        "signer_identity": signature_obj.signer_identity,
        "timestamp": signature_obj.timestamp.isoformat(),
        "signature_value": signature_obj.signature_value
    }

    # Validate with Pydantic
    cart_mandate = CartMandate(**mandate_data)

    # Store in database
    db_mandate = MandateModel(
        id=mandate_id,
        mandate_type="cart",
        user_id=user_id,
        transaction_id=None,
        mandate_data=json.dumps(mandate_data),
        signer_identity=signer_identity,
        signature=signature_obj.signature_value,
        signature_metadata=json.dumps({
            "algorithm": signature_obj.algorithm,
            "timestamp": signature_obj.timestamp.isoformat(),
            "signed_by": signed_by
        }),
        validation_status="valid",
    )

    db.add(db_mandate)
    await db.commit()
    await db.refresh(db_mandate)

    logger.info(f"Created Cart mandate: {mandate_id}, signed_by={signed_by}, intent_ref={intent_reference}")

    return cart_mandate


# ============================================================================
# Payment Mandate Creation
# ============================================================================

async def create_payment_mandate(
    db: AsyncSession,
    user_id: str,
    cart_reference: str,
    intent_reference: Optional[str],
    amount_cents: int,
    payment_credentials: str,
    human_not_present: bool = False
) -> PaymentMandate:
    """
    Create and store Payment mandate (always signed by payment agent).

    Args:
        db: Database session
        user_id: User identifier
        cart_reference: Cart mandate ID
        intent_reference: Intent mandate ID (optional for HP, required for HNP)
        amount_cents: Payment amount in cents
        payment_credentials: Tokenized payment credential
        human_not_present: True for HNP autonomous purchases

    Returns:
        Created PaymentMandate

    AP2 Compliance:
    - Always signed by Payment Agent
    - References Cart and optionally Intent
    - Uses tokenized credentials only
    """
    # Generate mandate ID
    mandate_id = f"payment_{uuid.uuid4().hex[:16]}"

    # Build mandate data without signature
    timestamp = datetime.utcnow()
    mandate_data = {
        "mandate_id": mandate_id,
        "mandate_type": "payment",
        "user_id": user_id,
        "references": cart_reference,
        "intent_reference": intent_reference,
        "amount_cents": amount_cents,
        "currency": "USD",
        "payment_credentials": payment_credentials,
        "human_not_present": human_not_present,
        "timestamp": timestamp.isoformat(),
    }

    # Sign with payment agent
    signature_obj = sign_payment_mandate(mandate_data)

    mandate_data["signature"] = {
        "algorithm": signature_obj.algorithm,
        "signer_identity": signature_obj.signer_identity,
        "timestamp": signature_obj.timestamp.isoformat(),
        "signature_value": signature_obj.signature_value
    }

    # Validate with Pydantic
    payment_mandate = PaymentMandate(**mandate_data)

    # Store in database
    db_mandate = MandateModel(
        id=mandate_id,
        mandate_type="payment",
        user_id=user_id,
        transaction_id=None,
        mandate_data=json.dumps(mandate_data),
        signer_identity="payment_agent",
        signature=signature_obj.signature_value,
        signature_metadata=json.dumps({
            "algorithm": signature_obj.algorithm,
            "timestamp": signature_obj.timestamp.isoformat(),
            "signed_by": "payment_agent"
        }),
        validation_status="valid",
    )

    db.add(db_mandate)
    await db.commit()
    await db.refresh(db_mandate)

    logger.info(f"Created Payment mandate: {mandate_id}, amount={amount_cents}¢, hnp={human_not_present}")

    return payment_mandate


# ============================================================================
# Mandate Retrieval
# ============================================================================

async def get_mandate_by_id(
    db: AsyncSession,
    mandate_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve mandate by ID.

    Args:
        db: Database session
        mandate_id: Mandate identifier

    Returns:
        Mandate data dict or None if not found
    """
    result = await db.execute(
        select(MandateModel).where(MandateModel.id == mandate_id)
    )
    mandate = result.scalar_one_or_none()

    if not mandate:
        return None

    return json.loads(mandate.mandate_data)


async def update_mandate_transaction_id(
    db: AsyncSession,
    mandate_id: str,
    transaction_id: str
) -> None:
    """
    Update mandate with transaction ID after processing.

    Args:
        db: Database session
        mandate_id: Mandate identifier
        transaction_id: Transaction identifier to link
    """
    result = await db.execute(
        select(MandateModel).where(MandateModel.id == mandate_id)
    )
    mandate = result.scalar_one_or_none()

    if mandate:
        mandate.transaction_id = transaction_id
        mandate.updated_at = datetime.utcnow()
        await db.commit()
        logger.info(f"Updated mandate {mandate_id} with transaction {transaction_id}")
