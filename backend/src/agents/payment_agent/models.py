"""
AP2 Mandate Models - Isolated Payment Agent Copy

⚠️ NO IMPORTS FROM PARENT PROJECT ⚠️

These models are REDEFINED here (not imported) to maintain Payment Agent isolation.
This allows the entire payment_agent/ directory to be extracted and reused in
any project without GhostCart dependencies.

Based on AP2 Protocol v0.1 specification.
"""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal, List
from datetime import datetime


# ============================================================================
# Signature Models
# ============================================================================

class SignatureObject(BaseModel):
    """
    Cryptographic signature for mandate authentication.

    AP2 Spec: All mandates (except HP context-only Intent) must be signed.
    """
    algorithm: Literal["HMAC-SHA256"]
    signer_identity: str
    timestamp: datetime
    signature_value: str = Field(pattern="^[0-9a-f]{64}$")

    model_config = {
        "strict": True,
        "extra": "forbid"
    }

    @field_validator("timestamp", mode="before")
    @classmethod
    def parse_timestamp(cls, v):
        """Accept both datetime objects and ISO strings (for JSON serialization compatibility)."""
        if isinstance(v, str):
            return datetime.fromisoformat(v)
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_not_future(cls, v: datetime):
        if v > datetime.utcnow():
            raise ValueError("Signature timestamp cannot be in the future")
        return v


# ============================================================================
# Intent Mandate (Authorization for HNP, Context for HP)
# ============================================================================

class ConstraintsObject(BaseModel):
    """User-defined constraints for autonomous purchases."""
    max_price_cents: Optional[int] = Field(None, ge=0)
    max_delivery_days: Optional[int] = Field(None, ge=0)
    currency: Literal["USD"] = "USD"

    model_config = {
        "strict": True,
        "extra": "forbid"
    }


class IntentMandate(BaseModel):
    """
    User's purchase intent - either context-only (HP) or pre-authorization (HNP).

    AP2 Compliance:
    - HP: Unsigned, context-only, immediate purchase
    - HNP: Signed, with constraints and expiration, autonomous purchase
    """
    mandate_id: str = Field(pattern="^intent_(hp|hnp)_")
    mandate_type: Literal["intent"] = "intent"
    user_id: str
    scenario: Literal["human_present", "human_not_present"]
    product_query: str
    constraints: Optional[ConstraintsObject] = None
    expiration: Optional[datetime] = None
    signature: Optional[SignatureObject] = None

    model_config = {
        "strict": False,  # Allow datetime string conversion
        "extra": "forbid"
    }

    @field_validator('expiration', mode='before')
    @classmethod
    def parse_expiration(cls, v):
        """Convert ISO datetime string to datetime object."""
        if v is None:
            return None
        if isinstance(v, str):
            # Parse ISO format datetime string
            from dateutil import parser
            return parser.isoparse(v)
        return v

    @model_validator(mode='after')
    def validate_hnp_requirements(self):
        """HNP flow requires signature, constraints, and expiration."""
        if self.scenario == "human_not_present":
            if not self.constraints or not self.expiration or not self.signature:
                raise ValueError(
                    "HNP Intent requires constraints, expiration, and signature"
                )
        return self


# ============================================================================
# Cart Mandate (Shopping basket)
# ============================================================================

class LineItem(BaseModel):
    """Individual item in shopping cart."""
    product_id: str
    product_name: str
    quantity: int = Field(ge=1)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)

    model_config = {
        "strict": True,
        "extra": "forbid"
    }

    @model_validator(mode='after')
    def validate_line_total(self):
        """Verify line_total = quantity * unit_price."""
        expected = self.quantity * self.unit_price_cents
        if self.line_total_cents != expected:
            raise ValueError(
                f"Line total mismatch: {self.line_total_cents} != {self.quantity} * {self.unit_price_cents}"
            )
        return self


class TotalObject(BaseModel):
    """Cart total breakdown."""
    subtotal_cents: int = Field(ge=0)
    tax_cents: int = Field(ge=0)
    shipping_cents: int = Field(ge=0)
    grand_total_cents: int = Field(ge=0)
    currency: Literal["USD"] = "USD"

    model_config = {
        "strict": True,
        "extra": "forbid"
    }

    @model_validator(mode='after')
    def validate_grand_total(self):
        """Verify grand_total = subtotal + tax + shipping."""
        expected = self.subtotal_cents + self.tax_cents + self.shipping_cents
        if self.grand_total_cents != expected:
            raise ValueError(
                f"Grand total mismatch: {self.grand_total_cents} != {self.subtotal_cents} + {self.tax_cents} + {self.shipping_cents}"
            )
        return self


class MerchantInfo(BaseModel):
    """Merchant identification."""
    merchant_id: str
    merchant_name: str
    merchant_url: str

    model_config = {
        "strict": True,
        "extra": "forbid"
    }


class ReferencesObject(BaseModel):
    """References to other mandates in the chain."""
    intent_mandate_id: Optional[str] = None
    transaction_id: Optional[str] = None

    model_config = {
        "strict": True,
        "extra": "forbid"
    }


class CartMandate(BaseModel):
    """
    Shopping cart with line items and totals.

    AP2 Compliance:
    - HP: Signed by user
    - HNP: Signed by agent, must reference Intent ID
    """
    mandate_id: str = Field(pattern="^cart_(hp|hnp)_")
    mandate_type: Literal["cart"] = "cart"
    items: List[LineItem]
    total: TotalObject
    merchant_info: MerchantInfo
    delivery_estimate_days: int = Field(ge=0)
    references: ReferencesObject
    signature: SignatureObject

    model_config = {
        "strict": False,  # Allow some flexibility for demo
        "extra": "forbid"
    }

    @model_validator(mode='after')
    def validate_totals_match_items(self):
        """Verify cart total.subtotal matches sum of line items."""
        items_total = sum(item.line_total_cents for item in self.items)
        if self.total.subtotal_cents != items_total:
            raise ValueError(
                f"Cart subtotal {self.total.subtotal_cents} != sum of items {items_total}"
            )
        return self


# ============================================================================
# Payment Mandate (Authorization request)
# ============================================================================

class PaymentMandate(BaseModel):
    """
    Payment authorization request with tokenized credentials.

    AP2 Compliance:
    - Always signed by Payment Agent
    - References Cart ID (and optionally Intent ID for HNP)
    - Uses tokenized credentials (never raw card data)
    - human_not_present flag for autonomous purchases
    """
    mandate_id: str = Field(pattern="^payment_")
    mandate_type: Literal["payment"] = "payment"
    user_id: str
    references: str = Field(pattern="^cart_(hp|hnp)_")  # Cart ID
    intent_reference: Optional[str] = Field(None, pattern="^intent_(hp|hnp)_")  # Intent ID (HNP only)
    amount_cents: int = Field(ge=0)
    currency: Literal["USD"] = "USD"
    payment_credentials: str = Field(pattern="^tok_")  # Tokenized payment method
    human_not_present: bool = False
    timestamp: datetime
    signature: SignatureObject

    model_config = {
        "strict": True,
        "extra": "forbid"
    }
