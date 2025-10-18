# Data Model: GhostCart AP2 Protocol Demonstration

**Feature**: GhostCart - AP2 Protocol Demonstration
**Date**: 2025-10-17
**Phase**: 1 - Design & Contracts

## Overview

This document defines the complete data model for GhostCart, including AP2 mandate structures (Intent, Cart, Payment), database schema (SQLite tables), and entity relationships for the human-present and human-not-present purchase flows.

## AP2 Mandate Entities (Pydantic Models)

These models implement the Agent Payments Protocol v0.1 specification from https://ap2-protocol.org/specification/

### SignatureObject

Represents cryptographic signature metadata for any mandate.

**Fields**:
- `algorithm` (string, required): Always `"HMAC-SHA256"` for demo (mocks production ECDSA)
- `signer_identity` (string, required): Identifier of who signed (user ID, agent ID, payment agent ID)
- `timestamp` (datetime, required): When signature was created (ISO 8601 format)
- `signature_value` (string, required): HMAC digest in hexadecimal format

**Validation Rules**:
- `algorithm` must be exactly `"HMAC-SHA256"`
- `signer_identity` must match expected signer for mandate type
- `timestamp` must not be in the future
- `signature_value` must be 64-character hex string (SHA256 output)

### IntentMandate

Captures user's original request for either immediate purchase (HP flow) or autonomous monitoring (HNP flow).

**Fields**:
- `mandate_id` (string, required): Unique identifier with prefix `intent_hp_` or `intent_hnp_`
- `mandate_type` (literal["intent"], required): Always `"intent"`
- `user_id` (string, required): User identifier
- `scenario` (literal["human_present", "human_not_present"], required): Flow type
- `product_query` (string, required): User's search terms or product description
- `constraints` (ConstraintsObject, optional): Price and delivery constraints for HNP flow
- `expiration` (datetime, required for HNP): When Intent authority expires (7 days default)
- `signature` (SignatureObject, required for HNP, optional for HP): User signature for pre-authorization

**Nested Type - ConstraintsObject**:
- `max_price_cents` (int, required): Maximum price willing to pay in cents
- `max_delivery_days` (int, required): Maximum acceptable delivery time in days
- `currency` (literal["USD"], required): Always USD per constitution

**Validation Rules**:
- If `scenario == "human_not_present"`: `constraints` required, `expiration` required, `signature` required
- If `scenario == "human_present"`: `signature` optional (audit trail only)
- `expiration` must be between 1 hour and 30 days in future
- `constraints.max_price_cents` must be positive
- `constraints.max_delivery_days` must be positive and ≤ 30

**AP2 Compliance Notes**:
- HP flow: Intent created for audit trail but does NOT require user signature per AP2
- HNP flow: Intent MUST have user signature as pre-authorization per AP2

### CartMandate

Represents exact items to be purchased with prices and totals.

**Fields**:
- `mandate_id` (string, required): Unique identifier with prefix `cart_`
- `mandate_type` (literal["cart"], required): Always `"cart"`
- `items` (list[LineItem], required): Products in cart with quantities and prices
- `total` (TotalObject, required): Subtotal, tax, shipping, grand total
- `merchant_info` (MerchantInfo, required): Merchant identifier and metadata
- `delivery_estimate_days` (int, required): Estimated delivery time in days
- `references` (ReferencesObject, required): Links to other mandates in chain
- `signature` (SignatureObject, required): Signer identity varies by flow

**Nested Type - LineItem**:
- `product_id` (string, required): Product identifier from merchant catalog
- `product_name` (string, required): Product display name
- `quantity` (int, required): Number of items
- `unit_price_cents` (int, required): Price per item in cents
- `line_total_cents` (int, required): quantity × unit_price_cents

**Nested Type - TotalObject**:
- `subtotal_cents` (int, required): Sum of all line totals
- `tax_cents` (int, required): Sales tax (mock calculation for demo)
- `shipping_cents` (int, required): Shipping cost
- `grand_total_cents` (int, required): subtotal + tax + shipping
- `currency` (literal["USD"], required): Always USD

**Nested Type - MerchantInfo**:
- `merchant_id` (string, required): Merchant identifier (mock: `"ghostcart_demo"`)
- `merchant_name` (string, required): Merchant display name
- `merchant_url` (string, required): Merchant website (mock URL)

**Nested Type - ReferencesObject**:
- `intent_mandate_id` (string, required for HNP, optional for HP): Links to Intent for chain validation
- `transaction_id` (string, optional): Groups mandates for same transaction

**Validation Rules**:
- All `line_total_cents` must equal `quantity × unit_price_cents`
- `total.subtotal_cents` must equal sum of all line totals
- `total.grand_total_cents` must equal `subtotal + tax + shipping`
- If HNP flow: `references.intent_mandate_id` required, signature must be agent
- If HP flow: `references.intent_mandate_id` optional, signature must be user
- `delivery_estimate_days` must match constraint from Intent if HNP flow

**AP2 Compliance Notes**:
- HP flow: Cart MUST have user signature as authorization per AP2
- HNP flow: Cart has agent signature (NOT user) per AP2, MUST reference Intent ID

### PaymentMandate

Created by Payment Agent to process payment with tokenized credentials.

**Fields**:
- `mandate_id` (string, required): Unique identifier with prefix `payment_`
- `mandate_type` (literal["payment"], required): Always `"payment"`
- `references` (PaymentReferencesObject, required): Links to Cart mandate
- `amount_cents` (int, required): Total to charge in cents (must match Cart grand total)
- `currency` (literal["USD"], required): Always USD
- `payment_credentials` (PaymentCredentials, required): Tokenized payment method
- `human_not_present` (bool, required): Flag signaling autonomous transaction to payment network
- `timestamp` (datetime, required): When payment mandate created
- `signature` (SignatureObject, required): Always signed by payment agent

**Nested Type - PaymentReferencesObject**:
- `cart_mandate_id` (string, required): Links to Cart for mandate chain
- `transaction_id` (string, required): Groups all mandates for transaction

**Nested Type - PaymentCredentials**:
- `payment_token` (string, required): Tokenized credential (e.g., `tok_visa_4242`)
- `payment_method_type` (string, required): Brand (visa, mastercard, amex, etc.)
- `last_four_digits` (string, required): Last 4 digits for user confirmation
- `expiration_month` (int, required): Card expiration month (1-12)
- `expiration_year` (int, required): Card expiration year (YYYY)
- `billing_address` (AddressObject, optional): Mock billing address

**Nested Type - AddressObject**:
- `street` (string, required)
- `city` (string, required)
- `state` (string, required)
- `postal_code` (string, required)
- `country` (literal["US"], required): US only for demo

**Validation Rules**:
- `amount_cents` must be positive
- `payment_credentials.payment_token` must start with `tok_`
- `payment_credentials.expiration_month` must be 1-12
- `payment_credentials.expiration_year` must be current year or future
- `signature.signer_identity` must be payment agent ID
- If HNP flow: `human_not_present` must be true

**AP2 Compliance Notes**:
- Payment Agent retrieves tokenized credentials, never raw payment data per AP2 role separation
- `human_not_present` flag signals to payment network this is autonomous transaction per AP2

### Transaction

Final result of payment processing with authorization or decline details.

**Fields**:
- `transaction_id` (string, required): Unique identifier with prefix `txn_`
- `intent_mandate_id` (string, optional): Links to Intent (nullable for HP flow context-only)
- `cart_mandate_id` (string, required): Links to Cart
- `payment_mandate_id` (string, required): Links to Payment
- `user_id` (string, required): User identifier
- `status` (literal["authorized", "declined", "expired", "failed"], required): Transaction outcome
- `authorization_code` (string, optional): Processor auth code on success (e.g., `AUTH_xy45z8`)
- `decline_reason` (string, optional): Specific reason on decline
- `decline_code` (literal, optional): AP2 error code (e.g., `ap2:payment:declined`)
- `amount_cents` (int, required): Total charged or attempted
- `currency` (literal["USD"], required): Always USD
- `created_at` (datetime, required): Transaction timestamp

**Validation Rules**:
- If `status == "authorized"`: `authorization_code` required, `decline_reason` null
- If `status == "declined"`: `decline_reason` required, `decline_code` required, `authorization_code` null
- `amount_cents` must match Payment Mandate amount

## Database Schema (SQLite)

### mandates Table

Stores all Intent, Cart, and Payment mandates with complete metadata and signatures.

**Schema**:
```sql
CREATE TABLE mandates (
    id TEXT PRIMARY KEY,  -- Mandate ID (intent_hp_abc123, cart_xyz789, payment_def456)
    mandate_type TEXT NOT NULL CHECK(mandate_type IN ('intent', 'cart', 'payment')),
    user_id TEXT NOT NULL,
    transaction_id TEXT,  -- Groups related mandates, nullable until transaction created
    mandate_data TEXT NOT NULL,  -- Complete JSON of Pydantic model
    signer_identity TEXT NOT NULL,
    signature TEXT NOT NULL,
    signature_metadata TEXT NOT NULL,  -- JSON with algorithm, timestamp, signer details
    validation_status TEXT NOT NULL CHECK(validation_status IN ('valid', 'invalid', 'unsigned')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_mandates_user_id ON mandates(user_id);
CREATE INDEX idx_mandates_transaction_id ON mandates(transaction_id);
CREATE INDEX idx_mandates_type ON mandates(mandate_type);
CREATE INDEX idx_mandates_created ON mandates(created_at DESC);
```

**Relationships**:
- Groups mandates by `transaction_id` for chain reconstruction
- `user_id` links to sessions table (logical, no FK for demo simplicity)

### monitoring_jobs Table

Stores background monitoring jobs for HNP flow with APScheduler integration.

**Schema**:
```sql
CREATE TABLE monitoring_jobs (
    job_id TEXT PRIMARY KEY,  -- APScheduler job identifier
    intent_mandate_id TEXT NOT NULL,  -- Links to Intent Mandate
    user_id TEXT NOT NULL,
    product_query TEXT NOT NULL,
    constraints TEXT NOT NULL,  -- JSON: {max_price_cents, max_delivery_days}
    schedule_interval_minutes INTEGER NOT NULL DEFAULT 5,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    last_check_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,  -- From Intent expiration field
    FOREIGN KEY (intent_mandate_id) REFERENCES mandates(id)
);

CREATE INDEX idx_monitoring_user_id ON monitoring_jobs(user_id);
CREATE INDEX idx_monitoring_active ON monitoring_jobs(active);
CREATE INDEX idx_monitoring_expires ON monitoring_jobs(expires_at);
```

**Relationships**:
- `intent_mandate_id` foreign key to mandates table
- APScheduler stores job metadata in separate table (managed by SQLAlchemyJobStore)

**Lifecycle**:
- Created when user signs Intent Mandate in HNP flow
- `active` set to false when conditions met and purchase completes
- `active` set to false when `expires_at` reached without conditions being met
- Job removed from APScheduler when `active` becomes false

### transactions Table

Stores transaction results with authorization or decline details.

**Schema**:
```sql
CREATE TABLE transactions (
    transaction_id TEXT PRIMARY KEY,  -- txn_abc123
    intent_mandate_id TEXT,  -- Nullable for HP flow context-only
    cart_mandate_id TEXT NOT NULL,
    payment_mandate_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('authorized', 'declined', 'expired', 'failed')),
    authorization_code TEXT,  -- On success
    decline_reason TEXT,  -- On failure
    decline_code TEXT,  -- AP2 error code
    amount_cents INTEGER NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (intent_mandate_id) REFERENCES mandates(id),
    FOREIGN KEY (cart_mandate_id) REFERENCES mandates(id),
    FOREIGN KEY (payment_mandate_id) REFERENCES mandates(id)
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_status ON transactions(status);
CREATE INDEX idx_transactions_created ON transactions(created_at DESC);
```

**Relationships**:
- Foreign keys to all three mandate types for complete chain
- `intent_mandate_id` nullable for HP flow where Intent is context-only

### sessions Table

Stores user session data for conversation continuity across messages.

**Schema**:
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,  -- UUID v4
    user_id TEXT NOT NULL,
    current_flow_type TEXT CHECK(current_flow_type IN ('hp', 'hnp', 'none')),
    context_data TEXT,  -- JSON for session state
    last_activity_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_activity ON sessions(last_activity_at DESC);
```

**Context Data JSON Structure**:
```json
{
  "current_mandate_id": "string",
  "current_products": [...],
  "current_cart": {...},
  "monitoring_jobs": [...]
}
```

**Lifecycle**:
- Created on first user message
- Updated on each message with `last_activity_at` timestamp
- Sessions older than 24 hours can be purged (cleanup job)

## Entity Relationships Diagram

```
┌─────────────────┐
│   sessions      │
│  (session_id)   │
└────────┬────────┘
         │ user_id
         ▼
┌─────────────────────────────────────────┐
│            mandates                     │
│  ┌─────────────────────────────────┐   │
│  │ Intent (scenario: HP)           │   │
│  │ - No user signature required    │   │
│  │ - Audit trail only              │   │
│  └─────────────┬───────────────────┘   │
│                │ referenced by          │
│  ┌─────────────▼───────────────────┐   │
│  │ Cart (HP flow)                  │   │
│  │ - User signature (auth)         │   │
│  └─────────────┬───────────────────┘   │
│                │ referenced by          │
│  ┌─────────────▼───────────────────┐   │
│  │ Payment                         │   │
│  │ - Payment agent signature       │   │
│  │ - human_not_present: false      │   │
│  └─────────────┬───────────────────┘   │
│                │                        │
│  ┌─────────────▼───────────────────┐   │
│  │ Intent (scenario: HNP)          │   │
│  │ - User signature (pre-auth)     │   │
│  └─────────────┬───────────────────┘   │
│                │ referenced by          │
│                │ + triggers job         │
│                │                        │
│  ┌─────────────▼───────────────────┐   │
│  │ Cart (HNP flow)                 │   │
│  │ - Agent signature               │   │
│  │ - References intent_id          │   │
│  └─────────────┬───────────────────┘   │
│                │ referenced by          │
│  ┌─────────────▼───────────────────┐   │
│  │ Payment                         │   │
│  │ - Payment agent signature       │   │
│  │ - human_not_present: true       │   │
│  └─────────────┬───────────────────┘   │
└────────────────┼────────────────────────┘
                 │ all linked by
                 ▼
         ┌───────────────┐
         │ transactions  │
         │(transaction_id)│
         └───────────────┘
                 ▲
                 │ intent_mandate_id
┌────────────────┴──────────┐
│   monitoring_jobs         │
│ - Created when Intent     │
│   signed in HNP flow      │
│ - APScheduler job runs    │
│   every 5 minutes         │
│ - Checks product price    │
│   and availability        │
│ - Triggers autonomous     │
│   purchase when           │
│   conditions met          │
└───────────────────────────┘
```

## Mandate Chain Flow

### Human-Present Flow (Immediate Purchase)

```
User Search Query
      ↓
[1] Intent Mandate Created
    - scenario: "human_present"
    - product_query: "coffee maker under 70 dollars"
    - signature: OPTIONAL (audit only)
    - Stored in mandates table
      ↓
User Selects Product
      ↓
[2] Cart Mandate Created
    - items: [Philips HD7462, qty: 1, $69]
    - total: {subtotal: $69, tax: $5, shipping: $0, grand_total: $74}
    - references.intent_mandate_id: OPTIONAL (context)
    - signature: REQUIRED (user signs) ← AUTHORIZATION
    - Stored in mandates table
      ↓
User Approves Cart (Signs)
      ↓
[3] Payment Mandate Created
    - amount: $74 (matches cart grand_total)
    - payment_credentials: tokenized (tok_visa_4242)
    - human_not_present: false
    - references.cart_mandate_id: links to cart
    - signature: REQUIRED (payment agent signs)
    - Stored in mandates table
      ↓
Payment Processed
      ↓
[4] Transaction Created
    - status: "authorized"
    - authorization_code: "AUTH_xy45z8"
    - Links: intent (optional), cart, payment mandate IDs
    - All mandates updated with transaction_id
    - Stored in transactions table
```

### Human-Not-Present Flow (Autonomous Monitoring)

```
User Monitoring Request
      ↓
[1] Intent Mandate Created
    - scenario: "human_not_present"
    - product_query: "Apple AirPods Pro"
    - constraints: {max_price: $180, max_delivery: 2 days}
    - expiration: 7 days from now
    - signature: REQUIRED (user signs) ← PRE-AUTHORIZATION
    - Stored in mandates table
      ↓
User Signs Intent (Pre-Authorizes)
      ↓
[2] Monitoring Job Created
    - job_id: scheduled in APScheduler
    - intent_mandate_id: links to intent
    - schedule: every 5 minutes
    - expires_at: matches intent expiration
    - active: true
    - Stored in monitoring_jobs table
      ↓
Background Job Runs Every 5 Minutes
    - Queries mock merchant API
    - Checks: price ≤ $180 AND delivery ≤ 2 days
    - If conditions NOT met: log check, continue
      ↓
Conditions Met (Price $175, Delivery 1 day)
      ↓
[3] Cart Mandate Created (Autonomous)
    - items: [AirPods Pro, qty: 1, $175]
    - total: {grand_total: $175 + tax + shipping}
    - references.intent_mandate_id: REQUIRED ← CHAIN LINK
    - signature: REQUIRED (agent signs, NOT user) ← AUTONOMOUS
    - Validate: total ≤ intent.constraints.max_price
    - Validate: delivery ≤ intent.constraints.max_delivery
    - Stored in mandates table
      ↓
[4] Payment Mandate Created (Autonomous)
    - amount: matches cart grand_total
    - payment_credentials: tokenized
    - human_not_present: true ← SIGNALS AUTONOMOUS
    - references.cart_mandate_id: links to cart
    - signature: payment agent signs
    - Stored in mandates table
      ↓
Payment Processed
      ↓
[5] Transaction Created
    - status: "authorized"
    - authorization_code: generated
    - Links: intent, cart, payment mandate IDs
    - All mandates updated with transaction_id
    - Stored in transactions table
      ↓
[6] Monitoring Job Deactivated
    - active: false
    - Job removed from APScheduler
    - monitoring_jobs record preserved for history
```

## Validation Logic

### Mandate Chain Validation (Payment Agent)

**Human-Present Flow Validation**:
```python
def validate_hp_mandate_chain(cart_mandate: CartMandate, payment_mandate: PaymentMandate):
    # FR-005: Cart must have user signature
    if cart_mandate.signature.signer_identity != cart_mandate.user_id:
        raise AP2Error("ap2:mandate:signature_invalid", "Cart must be signed by user in HP flow")

    # Verify signature cryptographically
    if not verify_signature(cart_mandate):
        raise AP2Error("ap2:mandate:signature_invalid", "Cart signature verification failed")

    # FR-006: Payment must reference Cart
    if payment_mandate.references.cart_mandate_id != cart_mandate.mandate_id:
        raise AP2Error("ap2:mandate:chain_invalid", "Payment must reference Cart mandate")

    # Amounts must match
    if payment_mandate.amount_cents != cart_mandate.total.grand_total_cents:
        raise AP2Error("ap2:mandate:chain_invalid", "Payment amount must match Cart total")
```

**Human-Not-Present Flow Validation**:
```python
def validate_hnp_mandate_chain(
    intent_mandate: IntentMandate,
    cart_mandate: CartMandate,
    payment_mandate: PaymentMandate
):
    # FR-015: Intent must have user signature (pre-authorization)
    if intent_mandate.signature.signer_identity != intent_mandate.user_id:
        raise AP2Error("ap2:mandate:signature_invalid", "Intent must be signed by user in HNP flow")

    # Verify Intent signature
    if not verify_signature(intent_mandate):
        raise AP2Error("ap2:mandate:signature_invalid", "Intent signature verification failed")

    # FR-007: Intent must not be expired
    if datetime.utcnow() > intent_mandate.expiration:
        raise AP2Error("ap2:mandate:expired", "Intent mandate has expired")

    # FR-019: Cart must have agent signature (NOT user)
    if cart_mandate.signature.signer_identity == cart_mandate.user_id:
        raise AP2Error("ap2:mandate:signature_invalid", "Cart must be signed by agent in HNP flow, not user")

    # FR-020: Cart must reference Intent ID
    if cart_mandate.references.intent_mandate_id != intent_mandate.mandate_id:
        raise AP2Error("ap2:mandate:chain_invalid", "Cart must reference Intent mandate ID in HNP flow")

    # FR-022: Cart must not exceed Intent constraints
    if cart_mandate.total.grand_total_cents > intent_mandate.constraints.max_price_cents:
        raise AP2Error(
            "ap2:mandate:constraints_violated",
            f"Cart total ${cart_mandate.total.grand_total_cents/100} exceeds Intent max ${intent_mandate.constraints.max_price_cents/100}"
        )

    if cart_mandate.delivery_estimate_days > intent_mandate.constraints.max_delivery_days:
        raise AP2Error(
            "ap2:mandate:constraints_violated",
            f"Cart delivery {cart_mandate.delivery_estimate_days} days exceeds Intent max {intent_mandate.constraints.max_delivery_days} days"
        )

    # FR-021: Payment must have human_not_present flag
    if not payment_mandate.human_not_present:
        raise AP2Error("ap2:mandate:chain_invalid", "Payment must have human_not_present flag in HNP flow")

    # Payment must reference Cart
    if payment_mandate.references.cart_mandate_id != cart_mandate.mandate_id:
        raise AP2Error("ap2:mandate:chain_invalid", "Payment must reference Cart mandate")
```

## Mock Service Data Structures

### Product (Mock Merchant API)

```python
class Product:
    product_id: str  # "prod_coffee_001"
    name: str  # "Philips HD7462 Coffee Maker"
    description: str
    category: str  # "Kitchen"
    price_cents: int  # 6900 = $69.00
    stock_status: str  # "in_stock", "out_of_stock"
    delivery_estimate_days: int  # 2
    image_url: str  # Mock URL
```

### PaymentMethod (Mock Credentials Provider)

```python
class PaymentMethod:
    payment_token: str  # "tok_visa_4242"
    payment_method_type: str  # "visa"
    last_four_digits: str  # "4242"
    expiration_month: int  # 12
    expiration_year: int  # 2027
    billing_address: AddressObject  # Mock address
```

### AuthorizationResult (Mock Payment Processor)

```python
class AuthorizationResult:
    success: bool
    transaction_id: str  # "txn_abc123" if success
    authorization_code: str  # "AUTH_xy45z8" if success
    decline_reason: str  # Specific reason if declined
    error_code: str  # "ap2:payment:declined" if declined
```

## Summary

This data model provides:
- ✅ Complete AP2 mandate structures (Intent, Cart, Payment) with validation
- ✅ Database schema supporting mandate storage, monitoring jobs, transactions, sessions
- ✅ Entity relationships for both HP and HNP flows
- ✅ Validation logic ensuring AP2 compliance (signature requirements, chain links, constraints)
- ✅ Mock service interfaces for merchant, credentials provider, payment processor
- ✅ Clear separation between user-signed (authorization) and agent-signed (autonomous) mandates
- ✅ Support for complete mandate chain reconstruction for audit trail visualization

Next: Generate API contracts defining REST endpoints and request/response schemas.
