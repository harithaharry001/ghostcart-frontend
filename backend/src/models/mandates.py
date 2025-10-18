"""
Pydantic Mandate Models for AP2 Protocol

Implements IntentMandate, CartMandate, and PaymentMandate per AP2 v0.1 specification.
All models include strict validation and nested types matching official schemas.
"""
from datetime import datetime, timedelta
from typing import Optional, Literal, List
from pydantic import BaseModel, Field, field_validator, model_validator
from .signatures import SignatureObject


# ==================== Nested Types ====================

class ConstraintsObject(BaseModel):
    """Price and delivery constraints for HNP Intent mandates."""
    max_price_cents: int = Field(gt=0, description="Maximum price willing to pay in cents")
    max_delivery_days: int = Field(gt=0, le=30, description="Maximum delivery time in days")
    currency: Literal["USD"] = "USD"


class LineItem(BaseModel):
    """Individual product line item in cart."""
    product_id: str
    product_name: str
    quantity: int = Field(gt=0)
    unit_price_cents: int = Field(ge=0)
    line_total_cents: int = Field(ge=0)

    @model_validator(mode='after')
    def validate_line_total(self):
        """Ensure line total matches quantity × unit price."""
        expected = self.quantity * self.unit_price_cents
        if self.line_total_cents != expected:
            raise ValueError(f"Line total {self.line_total_cents} != quantity({self.quantity}) × price({self.unit_price_cents})")
        return self


class TotalObject(BaseModel):
    """Cart total breakdown."""
    subtotal_cents: int = Field(ge=0)
    tax_cents: int = Field(ge=0)
    shipping_cents: int = Field(ge=0)
    grand_total_cents: int = Field(ge=0)
    currency: Literal["USD"] = "USD"

    @model_validator(mode='after')
    def validate_grand_total(self):
        """Ensure grand total matches sum of components."""
        expected = self.subtotal_cents + self.tax_cents + self.shipping_cents
        if self.grand_total_cents != expected:
            raise ValueError(f"Grand total {self.grand_total_cents} != sum of components({expected})")
        return self


class MerchantInfo(BaseModel):
    """Merchant identification."""
    merchant_id: str
    merchant_name: str
    merchant_url: str


class ReferencesObject(BaseModel):
    """Links between mandates in chain."""
    intent_mandate_id: Optional[str] = None
    transaction_id: Optional[str] = None


class PaymentReferencesObject(BaseModel):
    """Payment mandate references."""
    cart_mandate_id: str
    transaction_id: str


class AddressObject(BaseModel):
    """Billing address."""
    street: str
    city: str
    state: str
    postal_code: str
    country: Literal["US"] = "US"


class PaymentCredentials(BaseModel):
    """Tokenized payment credentials (never raw card data)."""
    payment_token: str = Field(pattern="^tok_")
    payment_method_type: str
    last_four_digits: str = Field(pattern="^[0-9]{4}$")
    expiration_month: int = Field(ge=1, le=12)
    expiration_year: int = Field(ge=2025)
    billing_address: Optional[AddressObject] = None


# ==================== Main Mandate Models ====================

class IntentMandate(BaseModel):
    """
    Intent Mandate per AP2 specification.

    AP2 Compliance:
    - HP flow: Intent created for audit trail, signature OPTIONAL
    - HNP flow: Intent MUST have user signature as pre-authorization
    - Constraints and expiration required only for HNP
    """
    mandate_id: str = Field(pattern="^intent_(hp|hnp)_")
    mandate_type: Literal["intent"] = "intent"
    user_id: str
    scenario: Literal["human_present", "human_not_present"]
    product_query: str
    constraints: Optional[ConstraintsObject] = None
    expiration: Optional[datetime] = None
    signature: Optional[SignatureObject] = None

    @model_validator(mode='after')
    def validate_hnp_requirements(self):
        """Validate HNP flow requirements."""
        if self.scenario == "human_not_present":
            if not self.constraints:
                raise ValueError("HNP flow requires constraints")
            if not self.expiration:
                raise ValueError("HNP flow requires expiration")
            if not self.signature:
                raise ValueError("HNP flow requires user signature")
            if self.signature.signer_identity != self.user_id:
                raise ValueError("HNP Intent must be signed by user")

            # Validate expiration is reasonable (1 hour to 30 days)
            now = datetime.utcnow()
            if self.expiration <= now + timedelta(hours=1):
                raise ValueError("Expiration must be at least 1 hour in future")
            if self.expiration > now + timedelta(days=30):
                raise ValueError("Expiration cannot exceed 30 days")

        return self

    model_config = {"strict": True, "extra": "forbid"}


class CartMandate(BaseModel):
    """
    Cart Mandate per AP2 specification.

    AP2 Compliance:
    - HP flow: MUST have user signature (authorization)
    - HNP flow: Has agent signature, MUST reference Intent ID
    - All math must validate (line totals, grand total)
    """
    mandate_id: str = Field(pattern="^cart_")
    mandate_type: Literal["cart"] = "cart"
    items: List[LineItem]
    total: TotalObject
    merchant_info: MerchantInfo
    delivery_estimate_days: int = Field(ge=0)
    references: ReferencesObject
    signature: SignatureObject

    @model_validator(mode='after')
    def validate_totals(self):
        """Validate cart totals match line items."""
        expected_subtotal = sum(item.line_total_cents for item in self.items)
        if self.total.subtotal_cents != expected_subtotal:
            raise ValueError(f"Subtotal {self.total.subtotal_cents} != sum of line items({expected_subtotal})")
        return self

    model_config = {"strict": True, "extra": "forbid"}


class PaymentMandate(BaseModel):
    """
    Payment Mandate per AP2 specification.

    AP2 Compliance:
    - Always signed by payment agent
    - human_not_present flag signals autonomous transaction
    - Amount must match Cart grand total
    - Uses only tokenized credentials, never raw PCI data
    """
    mandate_id: str = Field(pattern="^payment_")
    mandate_type: Literal["payment"] = "payment"
    references: PaymentReferencesObject
    amount_cents: int = Field(gt=0)
    currency: Literal["USD"] = "USD"
    payment_credentials: PaymentCredentials
    human_not_present: bool
    timestamp: datetime
    signature: SignatureObject

    model_config = {"strict": True, "extra": "forbid"}
