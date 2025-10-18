"""
Payments API Endpoints

Provides access to tokenized payment methods via Credentials Provider.

AP2 Compliance:
- Returns only tokenized credentials (tok_* format)
- Never exposes raw card numbers or CVV
- Credentials Provider role separation per AP2 specification
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Dict, Any
import logging

from ..mocks.credentials_provider import get_payment_methods, get_default_payment_method

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/payment-methods")
async def get_payment_methods_endpoint(
    user_id: str = Query(..., description="User identifier")
) -> Dict[str, Any]:
    """
    Get tokenized payment methods for a user.

    Query Parameters:
        user_id: User identifier (required)

    Returns:
        {
            "user_id": str,
            "payment_methods": List[PaymentMethod],
            "count": int
        }

    Payment Method Structure:
        {
            "token": str,  # tok_* format (never raw card data)
            "type": str,  # visa, mastercard, amex
            "last_four": str,
            "expiry_month": int,
            "expiry_year": int,
            "cardholder_name": str,
            "billing_zip": str,
            "is_default": bool
        }

    Example:
        GET /api/payment-methods?user_id=user_demo_001

    AP2 Compliance:
        - Tokenized credentials only (no raw card data)
        - Credentials Provider never sees product/merchant data
        - Clean role separation per AP2 specification
    """
    logger.info(f"Retrieving payment methods for user: {user_id}")

    try:
        payment_methods = get_payment_methods(user_id)

        return {
            "user_id": user_id,
            "payment_methods": payment_methods,
            "count": len(payment_methods)
        }

    except ValueError as e:
        logger.warning(f"No payment methods for user {user_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "ap2:credentials:unavailable",
                "message": str(e),
                "details": {"user_id": user_id}
            }
        )


@router.get("/payment-methods/default")
async def get_default_payment_method_endpoint(
    user_id: str = Query(..., description="User identifier")
) -> Dict[str, Any]:
    """
    Get user's default payment method.

    Query Parameters:
        user_id: User identifier (required)

    Returns:
        Default PaymentMethod or 404 if none set

    Example:
        GET /api/payment-methods/default?user_id=user_demo_001

    AP2 Compliance:
        Used by autonomous agents for HNP flow purchases.
    """
    logger.info(f"Retrieving default payment method for user: {user_id}")

    try:
        default_method = get_default_payment_method(user_id)

        if not default_method:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ap2:credentials:unavailable",
                    "message": f"No default payment method set for user {user_id}",
                    "details": {"user_id": user_id}
                }
            )

        return {
            "user_id": user_id,
            "payment_method": default_method
        }

    except ValueError as e:
        logger.warning(f"No payment methods for user {user_id}: {e}")
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "ap2:credentials:unavailable",
                "message": str(e),
                "details": {"user_id": user_id}
            }
        )
