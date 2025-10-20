"""
Transactions API Endpoints

Provides transaction records and complete mandate chain retrieval.

AP2 Compliance:
- Transactions link Intent → Cart → Payment mandate chain
- Provides complete audit trail for transparency
- Includes all signatures for verification
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
import logging

from ..db.init_db import get_db
from ..services.transaction_service import (
    get_transaction_by_id,
    get_transaction_chain,
    get_user_transactions
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{transaction_id}")
async def get_transaction_endpoint(
    transaction_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get transaction details.

    Path Parameters:
        transaction_id: Transaction identifier

    Returns:
        Transaction details with mandate references

    Example:
        GET /api/transactions/txn_abc123
    """
    logger.debug(f"Retrieving transaction: {transaction_id}")

    transaction = await get_transaction_by_id(db, transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "transaction_not_found",
                "message": f"No transaction found with ID: {transaction_id}"
            }
        )

    return {
        "transaction_id": transaction.transaction_id,
        "user_id": transaction.user_id,
        "status": transaction.status,
        "authorization_code": transaction.authorization_code,
        "decline_reason": transaction.decline_reason,
        "amount_cents": transaction.amount_cents,
        "currency": transaction.currency,
        "intent_mandate_id": transaction.intent_mandate_id,
        "cart_mandate_id": transaction.cart_mandate_id,
        "payment_mandate_id": transaction.payment_mandate_id,
    }


@router.get("/{transaction_id}/chain")
async def get_transaction_chain_endpoint(
    transaction_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get complete mandate chain for a transaction.

    Path Parameters:
        transaction_id: Transaction identifier

    Returns:
        {
            "transaction": {...},
            "intent": {...} | null,  # Context-only for HP, signed for HNP
            "cart": {...},  # User-signed (HP) or agent-signed (HNP)
            "payment": {...},  # Always payment-agent-signed
            "flow_type": "human_present" | "human_not_present"
        }

    Use Cases:
        - Mandate chain visualization in UI
        - Audit trail review
        - Signature verification
        - AP2 compliance demonstration

    Example:
        GET /api/transactions/txn_abc123/chain

    AP2 Compliance:
        - Returns complete audit trail
        - Shows mandate linkage (Intent → Cart → Payment)
        - Includes all signatures for cryptographic verification
        - Demonstrates AP2 protocol flow (HP or HNP)
    """
    logger.info(f"Retrieving mandate chain for transaction: {transaction_id}")

    chain = await get_transaction_chain(db, transaction_id)

    if not chain:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "transaction_not_found",
                "message": f"No transaction found with ID: {transaction_id}"
            }
        )

    return chain


@router.get("/user/{user_id}")
async def get_user_transactions_endpoint(
    user_id: str,
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get transactions for a user.

    Path Parameters:
        user_id: User identifier

    Query Parameters:
        limit: Max results (1-100, default 10)
        offset: Pagination offset (default 0)

    Returns:
        {
            "user_id": str,
            "count": int,
            "transactions": List[Transaction]
        }

    Example:
        GET /api/transactions/user/user_demo_001?limit=20&offset=0
    """
    logger.debug(f"Retrieving transactions for user: {user_id}, limit={limit}, offset={offset}")

    transactions = await get_user_transactions(db, user_id, limit, offset)

    return {
        "user_id": user_id,
        "count": len(transactions),
        "transactions": [
            {
                "transaction_id": t.transaction_id,
                "status": t.status,
                "authorization_code": t.authorization_code,
                "decline_reason": t.decline_reason,
                "amount_cents": t.amount_cents,
                "currency": t.currency,
                "cart_mandate_id": t.cart_mandate_id,
                "intent_mandate_id": t.intent_mandate_id,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in transactions
        ]
    }
