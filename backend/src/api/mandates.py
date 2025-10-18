"""
Mandates API Endpoints

Provides mandate signing and retrieval functionality.

AP2 Compliance:
- User signs Cart (HP) or Intent (HNP)
- Agent signs Cart (HNP only)
- Signatures use HMAC-SHA256 for demo (mocks production ECDSA)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json
import logging

from ..db.models import MandateModel
from ..db.init_db import get_db
from ..services.signature_service import (
    sign_user_mandate,
    sign_agent_mandate,
    verify_user_signature,
    verify_agent_signature
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class SignMandateRequest(BaseModel):
    """Request to sign a mandate."""
    mandate_id: str
    mandate_type: str  # "intent", "cart", "payment"
    mandate_data: Dict[str, Any]
    signer_id: str  # User ID or agent ID
    signer_type: str  # "user" or "agent"


class SignMandateResponse(BaseModel):
    """Response with signed mandate."""
    mandate_id: str
    mandate_type: str
    signed_mandate: Dict[str, Any]
    signature: Dict[str, Any]


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/sign")
async def sign_mandate_endpoint(
    request: SignMandateRequest,
    db: AsyncSession = Depends(get_db)
) -> SignMandateResponse:
    """
    Sign a mandate with user or agent signature.

    Request Body:
        {
            "mandate_id": str,
            "mandate_type": str,  # "intent" or "cart"
            "mandate_data": Dict,  # Mandate without signature
            "signer_id": str,  # User ID or agent ID
            "signer_type": str  # "user" or "agent"
        }

    Returns:
        {
            "mandate_id": str,
            "mandate_type": str,
            "signed_mandate": Dict,  # With signature added
            "signature": Dict  # Signature object
        }

    Use Cases:
        - HP Flow: User signs Cart before payment
        - HNP Flow: User signs Intent for pre-authorization

    AP2 Compliance:
        - HP: Cart requires user signature
        - HNP: Intent requires user signature, Cart requires agent signature
        - Signatures use HMAC-SHA256 (mocking production ECDSA)
    """
    logger.info(
        f"Signing {request.mandate_type} mandate {request.mandate_id} "
        f"by {request.signer_type}: {request.signer_id}"
    )

    # CRITICAL: Remove signature field if present (cart may have signature:null from frontend)
    if "signature" in request.mandate_data:
        logger.warning(f"Removing existing signature field from mandate_data before signing")
        request.mandate_data.pop("signature")

    # Generate signature
    if request.signer_type == "user":
        signature_obj = sign_user_mandate(request.mandate_data, request.signer_id)
    elif request.signer_type == "agent":
        signature_obj = sign_agent_mandate(request.mandate_data, request.signer_id)
    else:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "invalid_signer_type",
                "message": f"Invalid signer_type: {request.signer_type}. Must be 'user' or 'agent'."
            }
        )

    # Add signature to mandate
    signed_mandate = request.mandate_data.copy()
    signed_mandate["signature"] = {
        "algorithm": signature_obj.algorithm,
        "signer_identity": signature_obj.signer_identity,
        "timestamp": signature_obj.timestamp.isoformat(),
        "signature_value": signature_obj.signature_value
    }

    # Update mandate in database
    result = await db.execute(
        select(MandateModel).where(MandateModel.id == request.mandate_id)
    )
    db_mandate = result.scalar_one_or_none()

    if db_mandate:
        # Update existing mandate with signature
        db_mandate.mandate_data = json.dumps(signed_mandate)
        db_mandate.signature = signature_obj.signature_value
        db_mandate.signer_identity = signature_obj.signer_identity
        db_mandate.signature_metadata = json.dumps({
            "algorithm": signature_obj.algorithm,
            "timestamp": signature_obj.timestamp.isoformat(),
            "signer_type": request.signer_type
        })
        db_mandate.validation_status = "valid"

        await db.commit()
        logger.info(f"Updated mandate {request.mandate_id} with signature")
    else:
        logger.warning(f"Mandate {request.mandate_id} not found in database, returning signed data only")

    return SignMandateResponse(
        mandate_id=request.mandate_id,
        mandate_type=request.mandate_type,
        signed_mandate=signed_mandate,
        signature={
            "algorithm": signature_obj.algorithm,
            "signer_identity": signature_obj.signer_identity,
            "timestamp": signature_obj.timestamp.isoformat(),
            "signature_value": signature_obj.signature_value
        }
    )


@router.get("/{mandate_id}")
async def get_mandate_endpoint(
    mandate_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Retrieve mandate by ID.

    Path Parameters:
        mandate_id: Mandate identifier

    Returns:
        Complete mandate data including signature

    Example:
        GET /api/mandates/intent_hp_abc123
        GET /api/mandates/cart_hnp_def456
    """
    logger.debug(f"Retrieving mandate: {mandate_id}")

    result = await db.execute(
        select(MandateModel).where(MandateModel.id == mandate_id)
    )
    db_mandate = result.scalar_one_or_none()

    if not db_mandate:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "mandate_not_found",
                "message": f"No mandate found with ID: {mandate_id}"
            }
        )

    mandate_data = json.loads(db_mandate.mandate_data)

    return {
        "mandate_id": mandate_id,
        "mandate_type": db_mandate.mandate_type,
        "user_id": db_mandate.user_id,
        "transaction_id": db_mandate.transaction_id,
        "validation_status": db_mandate.validation_status,
        "created_at": db_mandate.created_at.isoformat(),
        "mandate_data": mandate_data
    }


@router.post("/verify")
async def verify_mandate_signature_endpoint(
    mandate_data: Dict[str, Any],
    signer_type: str
) -> Dict[str, Any]:
    """
    Verify mandate signature.

    Request Body:
        {
            "mandate_data": Dict,  # Complete mandate with signature
            "signer_type": str  # "user" or "agent"
        }

    Returns:
        {
            "valid": bool,
            "signer_identity": str,
            "algorithm": str,
            "timestamp": str
        }

    Use Cases:
        - Verify user signed their Cart before payment
        - Verify agent signed Cart with Intent reference
        - Audit trail validation
    """
    if "signature" not in mandate_data:
        return {
            "valid": False,
            "error": "No signature present in mandate"
        }

    signature = mandate_data["signature"]
    mandate_without_sig = mandate_data.copy()
    mandate_without_sig.pop("signature")

    # Verify signature
    if signer_type == "user":
        valid = verify_user_signature(
            mandate_without_sig,
            signature
        )
    elif signer_type == "agent":
        valid = verify_agent_signature(
            mandate_without_sig,
            signature
        )
    else:
        return {
            "valid": False,
            "error": f"Invalid signer_type: {signer_type}"
        }

    return {
        "valid": valid,
        "signer_identity": signature.get("signer_identity"),
        "algorithm": signature.get("algorithm"),
        "timestamp": signature.get("timestamp")
    }
