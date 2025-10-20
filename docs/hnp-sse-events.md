# HNP Flow SSE Events Reference

**Last Updated**: After monitoring_service.py fixes for FR-018, FR-043, FR-048, FR-049

This document defines all Server-Sent Events (SSE) emitted during the Human-Not-Present monitoring flow.

## Event Flow Timeline

```
User signs Intent
      ↓
[monitoring_check_started] ← Every check interval (10 sec demo, 5 min prod)
      ↓
[monitoring_check_complete] ← After each check (conditions not met)
      ↓
      ... (repeats every interval)
      ↓
[autonomous_purchase_starting] ← When conditions ARE met
      ↓
[autonomous_cart_created]
      ↓
[autonomous_purchase_complete] ← Success
      OR
[autonomous_purchase_failed] ← Error during purchase
      OR
[monitoring_expired] ← After 7 days without conditions being met
```

---

## Event Definitions

### 1. `monitoring_check_started`

**When**: Emitted at the start of each periodic monitoring check

**Purpose**: Let user know system is actively checking prices

**Payload**:
```json
{
  "intent_id": "intent_hnp_abc123",
  "timestamp": "2025-10-20T14:35:00Z",
  "message": "Checking prices at 02:35 PM"
}
```

**UI Action**: Update status card with "Checking now..." indicator

---

### 2. `monitoring_check_complete` (Conditions NOT Met)

**When**: Emitted after each check when conditions are NOT satisfied

**Purpose**: Show current price vs target, explain why purchase didn't trigger

**Payload**:
```json
{
  "intent_id": "intent_hnp_abc123",
  "status": "conditions_not_met",
  "current_price_cents": 24900,
  "current_delivery_days": 2,
  "current_stock_status": "in_stock",
  "target_price_cents": 18000,
  "target_delivery_days": 2,
  "reason": "price $249.00 exceeds max $180.00",
  "message": "Current price: $249.00 - Conditions not met: price $249.00 exceeds max $180.00",
  "last_check_at": "2025-10-20T14:35:00Z"
}
```

**Possible Reasons**:
- `"price $X exceeds max $Y"`
- `"delivery Xd exceeds max Yd"`
- `"out of stock"`
- `"product_not_found"` (no products match query)
- Combined: `"price $249.00 exceeds max $180.00, delivery 5d exceeds max 2d"`

**UI Action**: Update status card with:
- Last checked timestamp
- Current price (with comparison to target)
- Reason text explaining why conditions not met

---

### 3. `autonomous_purchase_starting`

**When**: Conditions ARE met, autonomous purchase beginning

**Purpose**: Alert user that purchase is about to happen

**Payload**:
```json
{
  "intent_id": "intent_hnp_abc123",
  "product": {
    "name": "Apple AirPods Pro",
    "price_cents": 17500,
    "delivery_days": 1
  },
  "message": "Conditions met! Starting autonomous purchase..."
}
```

**UI Action**: Show prominent notification "Purchase starting!"

---

### 4. `autonomous_cart_created`

**When**: Agent has created and signed the Cart mandate

**Purpose**: Transparency - show Cart was created autonomously

**Payload**:
```json
{
  "cart_id": "cart_hnp_xyz789",
  "intent_id": "intent_hnp_abc123",
  "total_cents": 19140,
  "agent_signed": true
}
```

**UI Action**: Update notification with Cart details

---

### 5. `autonomous_purchase_complete`

**When**: Payment authorized successfully

**Purpose**: Notify user of successful autonomous purchase

**Payload**:
```json
{
  "transaction_id": "txn_def456",
  "authorization_code": "AUTH_xy45z8",
  "amount_cents": 19140,
  "product_name": "Apple AirPods Pro",
  "intent_id": "intent_hnp_abc123",
  "cart_id": "cart_hnp_xyz789"
}
```

**UI Action**:
- Large success notification
- Show transaction ID, authorization code
- Offer "View Chain" and "View Details" buttons
- Update monitoring status to "Completed - Purchase successful"

---

### 6. `autonomous_purchase_failed`

**When**: Payment declined or error during purchase

**Purpose**: Notify user of failure, provide error details

**Payload**:
```json
{
  "error": "Payment declined: Insufficient funds",
  "intent_id": "intent_hnp_abc123",
  "errors": ["ap2:payment:declined"]
}
```

**UI Action**:
- Show error notification
- Explain failure reason
- Monitoring remains active (will retry on next check if conditions still met)

---

### 7. `monitoring_expired`

**When**: Intent mandate reaches expiration (7 days) without conditions being met

**Purpose**: Notify user monitoring period ended, offer to create new monitoring

**Payload**:
```json
{
  "intent_id": "intent_hnp_abc123",
  "product_query": "Apple AirPods Pro",
  "target_price_cents": 18000,
  "current_price_cents": 24900,
  "message": "Monitoring expired after 7 days without conditions being met. Current price: $249.00",
  "action_available": "create_new_monitoring"
}
```

**UI Action**:
- Show expiration notification
- Display current price for reference
- Offer button: "Set Up New Monitoring" (pre-fills with same constraints)
- Update monitoring status to "Expired"

---

## Frontend Integration Notes

### Status Card Updates

The monitoring status card should listen for these events and update:

```jsx
useEffect(() => {
  eventSource.addEventListener('monitoring_check_started', (e) => {
    const data = JSON.parse(e.data);
    setStatusCard({
      status: 'checking',
      lastCheck: data.timestamp,
      message: data.message
    });
  });

  eventSource.addEventListener('monitoring_check_complete', (e) => {
    const data = JSON.parse(e.data);
    setStatusCard({
      status: 'active',
      lastCheck: data.last_check_at,
      currentPrice: data.current_price_cents / 100,
      targetPrice: data.target_price_cents / 100,
      reason: data.reason,
      message: data.message
    });
  });

  // ... other events
}, [eventSource]);
```

### Display Format Example

```
┌─────────────────────────────────────────────┐
│ Monitoring Active                            │
│ Product: Apple AirPods Pro                   │
│ Target: ≤ $180, delivery ≤ 2 days            │
│                                               │
│ Last checked: 2:35 PM                         │
│ Current price: $249.00                        │
│ Status: Conditions not met - price too high   │
│                                               │
│ Expires: Oct 27, 2025                         │
│ [Cancel Monitoring]                           │
└─────────────────────────────────────────────┘
```

---

## Testing the Events

### Backend Test (Manual)

1. Start backend: `uvicorn src.main:app --reload`
2. Connect to SSE endpoint: `curl -N http://localhost:8000/api/chat/sse?user_id=user_demo_001`
3. Trigger monitoring setup via chat
4. Watch SSE stream for events every 10 seconds (demo mode)

### Expected Output

```
event: monitoring_check_started
data: {"intent_id": "intent_hnp_...", "timestamp": "...", "message": "Checking prices at ..."}

event: monitoring_check_complete
data: {"status": "conditions_not_met", "current_price_cents": 24900, ...}

(10 seconds later)

event: monitoring_check_started
data: ...

event: monitoring_check_complete
data: ...

(repeats until conditions met)

event: autonomous_purchase_starting
data: ...

event: autonomous_cart_created
data: ...

event: autonomous_purchase_complete
data: {"transaction_id": "...", "authorization_code": "...", ...}
```

---

## Spec Compliance

These events satisfy the following functional requirements:

- ✅ **FR-018**: System updates status card after each check with timestamp, current price, and reason
- ✅ **FR-043**: System shows monitoring progress messages with timestamps and reasons
- ✅ **FR-048**: System differentiates between out-of-stock and price issues
- ✅ **FR-049**: System includes final price in expiration notification with option to recreate

---

## Implementation Notes

**Code Location**: `backend/src/services/monitoring_service.py`

**Key Functions**:
- `check_monitoring_conditions()` - Emits all check-related events
- Lines 181-187: `monitoring_check_started`
- Lines 238-245: `monitoring_check_complete` (product not found)
- Lines 282-293: `monitoring_check_complete` (conditions not met)
- Lines 202-219: `monitoring_expired`
- Lines 406-423: `autonomous_purchase_complete`

**SSE Manager**: Events are emitted via `sse_manager.add_event(user_id, event_type, payload)`
