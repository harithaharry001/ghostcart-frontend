# Bug Fixes & Implementation Changes

## 2025-10-19: HNP Flow Fixes

### Issue 1: Intent Signature Modal Not Appearing Consistently

**Problem:**
- HNP Intent signature modal would sometimes appear, sometimes not
- Agent was asking "Shall I set up this monitoring?" and then stopping
- Never called `create_hnp_intent` or `request_user_intent_signature` tools
- Supervisor would say "Monitoring Activated" prematurely

**Root Cause:**
- Ambiguous workflow in HNP agent system prompt
- Agent thought it needed to wait for another confirmation after asking "Shall I set up?"
- Never progressed to creating Intent mandate or requesting signature

**Fix:**
- **File:** `/backend/src/agents/hnp_delegate_strands.py`
- **Changes:**
  1. Rewrote workflow steps 3-5 to be explicit:
     - Step 3: Present summary and ask "Ready to set this up? I'll need your biometric authorization."
     - Step 4: After user confirms, IMMEDIATELY call both tools in sequence without waiting:
       - `create_hnp_intent` → receive Intent JSON
       - `request_user_intent_signature` with that Intent JSON
     - Step 5: Wait for user to complete signature before activating
  2. Updated Important Rules section to clarify the two-tool sequence
  3. Made it clear: "DO NOT wait between these two calls!"

**Result:** Signature modal now appears reliably every time after user confirms setup.

---

### Issue 2: Monitoring Job Not Actually Created

**Problem:**
- Agent said "Monitoring Activated!" but no monitoring job existed
- No database records created
- No APScheduler jobs scheduled
- No price drop registered
- `register_price_drop()` never called → demo price drop never happened

**Root Cause:**
- `activate_monitoring_wrapper` in `/backend/src/api/chat.py` was a mock/placeholder
- Function just returned fake response: `"message": "Monitoring job will be activated..."`
- Never called the real `create_monitoring_job()` function from `monitoring_service.py`

**Fix:**
- **File:** `/backend/src/api/chat.py` (lines 113-160)
- **Changes:**
  1. Completely rewrote `activate_monitoring_wrapper` to call real monitoring creation
  2. Added async-to-sync bridge using `asyncio.new_event_loop()`
  3. Created Payment Agent instance for autonomous purchases
  4. Called actual `create_monitoring_job()` with proper parameters
  5. This now properly:
     - Creates monitoring job record in database
     - Calls `register_price_drop(product_query, max_price_cents)` (line 117-120 of monitoring_service.py)
     - Schedules APScheduler job to run every 30 seconds
     - Returns real job details

**Code Before:**
```python
def activate_monitoring_wrapper(user_id: str, intent_mandate: Dict[str, Any]) -> Dict[str, Any]:
    """Activate monitoring job - returns job details"""
    from datetime import datetime
    from ..config import settings
    job_id = intent_mandate["mandate_id"]
    return {
        "job_id": job_id,
        "message": "Monitoring job will be activated after you sign the Intent mandate"
    }
```

**Code After:**
```python
def activate_monitoring_wrapper(user_id: str, intent_mandate: Dict[str, Any]) -> Dict[str, Any]:
    """Activate monitoring job - creates actual APScheduler job."""
    import asyncio
    from ..services.monitoring_service import create_monitoring_job
    from ..agents.payment_agent.agent import create_payment_agent
    from ..db.init_db import AsyncSessionLocal

    # Create Payment Agent
    payment_agent = create_payment_agent(...)

    # Run async create_monitoring_job in sync context
    async def _create_job():
        async with AsyncSessionLocal() as db:
            return await create_monitoring_job(
                db=db,
                intent_mandate=intent_mandate,
                payment_agent=payment_agent,
                sse_manager=None
            )

    # Execute async function
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(_create_job())
        return result
    finally:
        loop.close()
```

**Result:**
- Monitoring jobs now properly created in database
- APScheduler jobs scheduled correctly
- Price drops registered: `📉 DEMO: Price drop registered for 'coffee maker' to $40.00 (drops in 10 seconds)`
- Autonomous purchases trigger after price drop

---

### Issue 3: Frontend Not Storing Intent Mandate Data

**Problem:**
- Frontend tried to sign Intent mandates using `pendingCartData` (null for HNP flow)
- Signature request failed with 422 Unprocessable Entity
- Error: "Failed to sign mandate"

**Root Cause:**
- Frontend only had `pendingCartData` state for HP flow
- When `signature_requested` SSE event came for Intent, no Intent data was stored
- `handleSignatureConfirm` always sent `pendingCartData` regardless of mandate type

**Fix:**
- **File:** `/frontend/src/components/ChatInterface.jsx`
- **Changes:**
  1. Added `pendingIntentData` state to store Intent mandates separately (line 34)
  2. Updated `signature_requested` event handler to:
     - Check `mandate_type`
     - Store Intent data in `pendingIntentData` for HNP flow
     - Store cart data in `pendingCartData` for HP flow (line 212-218)
  3. Updated `handleSignatureConfirm` to:
     - Select correct data: `mandateType === 'intent' ? pendingIntentData : pendingCartData` (line 341)
     - Validate data exists before signing (line 343-345)
     - Send appropriate confirmation message based on type (line 381-383)

**Backend Support:**
- **File:** `/backend/src/agents/hnp_delegate_strands.py`
- Added Intent mandate data to SSE event payload (line 356)
- Updated `request_user_intent_signature` tool to accept `intent_mandate_json` parameter (line 324)

**Result:** Frontend now correctly signs Intent mandates with proper data.

---

## Demo Price Drop Implementation

### Feature: Automatic Price Drop After 10 Seconds

**Purpose:** Enable autonomous purchase demo without manual intervention.

**Files Modified:**

1. **`/backend/src/mocks/merchant_api.py`:**
   - Added `register_price_drop(product_query, target_price_cents)` function (lines 203-222)
   - Added `_apply_demo_price_drop(product, query)` function (lines 225-263)
   - Modified `search_products()` to apply price drops before filtering (lines 299-334)
   - Price drop threshold: 10 seconds (line 254, changed from 45 seconds)

2. **`/backend/src/services/monitoring_service.py`:**
   - Added `register_price_drop()` call when monitoring job created (lines 116-120)
   - Registers drop to `max_price_cents` from Intent constraints

**How It Works:**

```
T+0s   : Monitoring activated
         → register_price_drop("coffee maker", 4000) // $40 in cents
         → Log: "📉 DEMO: Price drop registered..."

T+10s  : Price drop threshold reached
         → _apply_demo_price_drop returns target price instead of original

T+30s  : First scheduled check
         → search_products sees dropped price
         → Log: "💰 DEMO: Price drop applied! $69.00 → $40.00"
         → Conditions met → trigger_autonomous_purchase()
         → Purchase complete! ✅
```

**Timeline:**
- **10 seconds:** Price drops to user's target
- **30 seconds:** First scheduled check sees drop, triggers purchase
- **Total demo time: ~30 seconds from setup to purchase**

---

## Additional Improvements

### HNP Agent System Prompt Clarity

**File:** `/backend/src/agents/hnp_delegate_strands.py`

**Changes:**
- Made 6-step workflow more explicit and sequential
- Added "DO NOT wait" warnings in multiple places
- Clarified that Intent creation and signature request happen together
- Updated example flow to show exact sequence
- Changed "Shall I set up?" to "Ready to set this up? I'll need your biometric authorization."

**Result:** Agent follows correct workflow consistently.

---

## Testing Checklist

- [x] HNP signature modal appears consistently
- [x] Intent mandate data included in SSE event
- [x] Frontend stores and signs Intent correctly
- [x] Monitoring job created in database
- [x] APScheduler job scheduled
- [x] Price drop registered
- [x] Price drop applied after 10 seconds
- [x] Autonomous purchase triggers at ~30 seconds
- [x] Full flow completes without manual intervention

---

## Known Issues / Future Improvements

1. **Auto-confirmation:** User still needs to type "Yes" after summary
   - **Suggestion:** Auto-send "Yes" from frontend after 1 second

2. **Error handling:** Need better error messages if monitoring creation fails
   - **Suggestion:** Add try/catch with user-friendly error SSE events

3. **SSE for monitoring events:** Current implementation doesn't send SSE events during monitoring
   - **Suggestion:** Add SSE manager to monitoring service for real-time updates

4. **Price drop realism:** All products drop to exact target price
   - **Suggestion:** Add randomization (drop to target ± 10%)

---

## Files Changed Summary

```
backend/src/agents/hnp_delegate_strands.py    - Fixed agent workflow & signature request
backend/src/api/chat.py                       - Fixed activate_monitoring_wrapper
backend/src/services/monitoring_service.py    - Added register_price_drop call
backend/src/mocks/merchant_api.py            - Implemented price drop system
frontend/src/components/ChatInterface.jsx     - Added Intent data handling
```
