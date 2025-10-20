"""
Transaction Service

Creates and retrieves transactions with complete mandate chain linkage.

AP2 Compliance:
- Transactions link Intent → Cart → Payment mandate chain
- Stores authorization results for audit trail
- Provides complete chain retrieval for transparency
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..db.models import TransactionModel, MandateModel
from ..models.transactions import Transaction

logger = logging.getLogger(__name__)


# ============================================================================
# Transaction Creation
# ============================================================================

async def create_transaction(
    db: AsyncSession,
    user_id: str,
    cart_mandate_id: str,
    payment_mandate_id: str,
    intent_mandate_id: Optional[str],
    status: str,  # "authorized", "declined", "expired", "failed"
    authorization_code: Optional[str] = None,
    decline_reason: Optional[str] = None,
    amount_cents: int = 0,
    processor_response: Optional[Dict[str, Any]] = None
) -> Transaction:
    """
    Create transaction record linking mandate chain.

    Args:
        db: Database session
        user_id: User identifier
        cart_mandate_id: Cart mandate ID
        payment_mandate_id: Payment mandate ID
        intent_mandate_id: Intent mandate ID (optional for HP, required for HNP)
        status: Transaction status
        authorization_code: Auth code if authorized
        decline_reason: Reason if declined
        amount_cents: Transaction amount
        processor_response: Full processor response for audit trail

    Returns:
        Created Transaction

    AP2 Compliance:
    - Links complete mandate chain for audit trail
    - Stores authorization or decline information
    - Transaction ID becomes permanent record identifier
    """
    # Generate transaction ID
    transaction_id = f"txn_{uuid.uuid4().hex[:16]}"
    created_at = datetime.utcnow()

    # Build transaction data
    transaction_data = {
        "transaction_id": transaction_id,
        "intent_mandate_id": intent_mandate_id,
        "cart_mandate_id": cart_mandate_id,
        "payment_mandate_id": payment_mandate_id,
        "user_id": user_id,
        "status": status,
        "authorization_code": authorization_code,
        "decline_reason": decline_reason,
        "amount_cents": amount_cents,
        "currency": "USD",
        "created_at": created_at
    }

    # Validate with Pydantic
    transaction = Transaction(**transaction_data)

    # Store in database
    db_transaction = TransactionModel(
        transaction_id=transaction_id,
        intent_mandate_id=intent_mandate_id,
        cart_mandate_id=cart_mandate_id,
        payment_mandate_id=payment_mandate_id,
        user_id=user_id,
        status=status,
        authorization_code=authorization_code,
        decline_reason=decline_reason,
        amount_cents=amount_cents,
        currency="USD"
    )

    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)

    # Update mandates with transaction ID
    await _link_mandates_to_transaction(
        db, transaction_id, intent_mandate_id, cart_mandate_id, payment_mandate_id
    )

    logger.info(
        f"Created transaction: {transaction_id}, status={status}, "
        f"cart={cart_mandate_id}, payment={payment_mandate_id}"
    )

    return transaction


async def _link_mandates_to_transaction(
    db: AsyncSession,
    transaction_id: str,
    intent_mandate_id: Optional[str],
    cart_mandate_id: str,
    payment_mandate_id: str
) -> None:
    """
    Update all mandates with transaction ID.

    Args:
        db: Database session
        transaction_id: Transaction identifier
        intent_mandate_id: Intent mandate ID (optional)
        cart_mandate_id: Cart mandate ID
        payment_mandate_id: Payment mandate ID
    """
    mandate_ids = [cart_mandate_id, payment_mandate_id]
    if intent_mandate_id:
        mandate_ids.append(intent_mandate_id)

    for mandate_id in mandate_ids:
        result = await db.execute(
            select(MandateModel).where(MandateModel.id == mandate_id)
        )
        mandate = result.scalar_one_or_none()

        if mandate:
            mandate.transaction_id = transaction_id
            mandate.updated_at = datetime.utcnow()

    await db.commit()
    logger.debug(f"Linked {len(mandate_ids)} mandates to transaction {transaction_id}")


# ============================================================================
# Transaction Retrieval
# ============================================================================

async def get_transaction_by_id(
    db: AsyncSession,
    transaction_id: str
) -> Optional[Transaction]:
    """
    Retrieve transaction by ID.

    Args:
        db: Database session
        transaction_id: Transaction identifier

    Returns:
        Transaction or None if not found
    """
    result = await db.execute(
        select(TransactionModel).where(TransactionModel.transaction_id == transaction_id)
    )
    db_transaction = result.scalar_one_or_none()

    if not db_transaction:
        return None

    # Convert to Pydantic model
    transaction = Transaction(
        transaction_id=db_transaction.transaction_id,
        intent_mandate_id=db_transaction.intent_mandate_id,
        cart_mandate_id=db_transaction.cart_mandate_id,
        payment_mandate_id=db_transaction.payment_mandate_id,
        user_id=db_transaction.user_id,
        status=db_transaction.status,
        authorization_code=db_transaction.authorization_code,
        decline_reason=db_transaction.decline_reason,
        amount_cents=db_transaction.amount_cents,
        currency=db_transaction.currency or "USD",
        created_at=db_transaction.created_at
    )

    return transaction


async def get_transaction_chain(
    db: AsyncSession,
    transaction_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve complete mandate chain for a transaction.

    Args:
        db: Database session
        transaction_id: Transaction identifier

    Returns:
        Complete chain dict with Intent, Cart, Payment, Transaction or None

    AP2 Compliance:
    - Returns full audit trail for transparency
    - Shows complete mandate linkage (Intent → Cart → Payment → Transaction)
    - Includes all signatures for verification
    """
    # Get transaction
    result = await db.execute(
        select(TransactionModel).where(TransactionModel.transaction_id == transaction_id)
    )
    db_transaction = result.scalar_one_or_none()

    if not db_transaction:
        return None

    # Get mandates
    intent_mandate = None
    cart_mandate = None
    payment_mandate = None

    # Get Intent (may be None for HP)
    if db_transaction.intent_mandate_id:
        result = await db.execute(
            select(MandateModel).where(
                MandateModel.id == db_transaction.intent_mandate_id
            )
        )
        intent_db = result.scalar_one_or_none()
        if intent_db:
            intent_mandate = json.loads(intent_db.mandate_data)

    # Get Cart
    result = await db.execute(
        select(MandateModel).where(MandateModel.id == db_transaction.cart_mandate_id)
    )
    cart_db = result.scalar_one_or_none()
    if cart_db:
        cart_mandate = json.loads(cart_db.mandate_data)

    # Get Payment
    result = await db.execute(
        select(MandateModel).where(
            MandateModel.id == db_transaction.payment_mandate_id
        )
    )
    payment_db = result.scalar_one_or_none()
    if payment_db:
        payment_mandate = json.loads(payment_db.mandate_data)

    # Build chain
    chain = {
        "transaction": {
            "transaction_id": db_transaction.transaction_id,
            "user_id": db_transaction.user_id,
            "status": db_transaction.status,
            "authorization_code": db_transaction.authorization_code,
            "decline_reason": db_transaction.decline_reason,
            "amount_cents": db_transaction.amount_cents,
            "currency": db_transaction.currency or "USD",
            "created_at": db_transaction.created_at.isoformat(),
        },
        "intent": intent_mandate,  # May be None for HP context-only
        "cart": cart_mandate,
        "payment": payment_mandate,
        "flow_type": "human_not_present" if intent_mandate and intent_mandate.get("signature") else "human_present",
    }

    logger.debug(f"Retrieved chain for transaction {transaction_id}")

    return chain


async def get_user_transactions(
    db: AsyncSession,
    user_id: str,
    limit: int = 10,
    offset: int = 0
) -> list[Transaction]:
    """
    Get transactions for a user.

    Args:
        db: Database session
        user_id: User identifier
        limit: Max results
        offset: Pagination offset

    Returns:
        List of transactions (most recent first)
    """
    result = await db.execute(
        select(TransactionModel)
        .where(TransactionModel.user_id == user_id)
        .order_by(TransactionModel.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    db_transactions = result.scalars().all()

    transactions = [
        Transaction(
            transaction_id=t.transaction_id,
            intent_mandate_id=t.intent_mandate_id,
            cart_mandate_id=t.cart_mandate_id,
            payment_mandate_id=t.payment_mandate_id,
            user_id=t.user_id,
            status=t.status,
            authorization_code=t.authorization_code,
            decline_reason=t.decline_reason,
            amount_cents=t.amount_cents,
            currency=t.currency or "USD",
            created_at=t.created_at
        )
        for t in db_transactions
    ]

    return transactions
