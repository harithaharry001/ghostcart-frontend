"""
Pydantic Transaction Model

Represents final transaction result with mandate chain links.
AP2 Compliance: Links to complete mandate chain for audit trail.
"""
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class Transaction(BaseModel):
    """
    Transaction result per AP2 specification.

    AP2 Compliance:
    - Links to complete mandate chain (Intent optional for HP)
    - Status indicates authorization or decline
    - Authorization code on success, decline reason on failure
    - All monetary values in cents
    """
    transaction_id: str = Field(pattern="^txn_")
    intent_mandate_id: Optional[str] = None  # Nullable for HP context-only
    cart_mandate_id: str
    payment_mandate_id: str
    user_id: str
    status: Literal["authorized", "declined", "expired", "failed"]
    authorization_code: Optional[str] = None  # Present on success
    decline_reason: Optional[str] = None  # Present on decline
    decline_code: Optional[str] = None  # AP2 error code
    amount_cents: int = Field(gt=0)
    currency: Literal["USD"] = "USD"
    created_at: datetime

    model_config = {
        "strict": True,
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "transaction_id": "txn_abc123",
                "intent_mandate_id": None,
                "cart_mandate_id": "cart_xyz789",
                "payment_mandate_id": "payment_def456",
                "user_id": "user_demo_001",
                "status": "authorized",
                "authorization_code": "AUTH_xy45z8",
                "decline_reason": None,
                "decline_code": None,
                "amount_cents": 7400,
                "currency": "USD",
                "created_at": "2025-10-17T14:35:00Z"
            }
        }
    }
