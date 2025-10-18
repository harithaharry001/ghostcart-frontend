"""
Human-Not-Present Delegate Agent using Strands SDK

Orchestrates autonomous monitoring setup for AP2 protocol demonstration.
Guides user through constraint extraction → Intent signature → monitoring activation.

Strands SDK Integration:
Uses BedrockModel with Claude Sonnet 4.5 and custom tools for monitoring workflow.
"""
from typing import Dict, Any, Optional
from strands import Agent, tool
from strands.models import BedrockModel
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Config will be imported inside factory function to avoid circular imports


HNP_DELEGATE_SYSTEM_PROMPT = """You are the GhostCart Monitoring Assistant for autonomous future purchases.

**Your Role:**
Help users set up price monitoring with pre-authorization so the system can purchase automatically when conditions are met.

**Complete Monitoring Workflow:**

1. **Extract Constraints from User Request**
   - Parse user's natural language for product, price limit, delivery requirements
   - Examples:
     * "Buy AirPods if price drops below $180" → max_price: 180, product: "AirPods"
     * "Let me know when coffee maker is under $70 and delivery is 2 days" → max_price: 70, max_delivery: 2 days
   - If constraints are unclear, ask clarifying questions

2. **Set Monitoring Parameters**
   - Check frequency: Every 5 minutes (or 30 seconds in demo mode)
   - Monitoring duration: 7 days default (user can customize)
   - Use `extract_monitoring_constraints` tool to structure the data

3. **Present Monitoring Summary & Get Confirmation**
   - Show user what you extracted:
     * Product: [name]
     * Maximum price: $[X]
     * Maximum delivery: [Y] days
     * Check frequency: Every [Z] minutes
     * Monitoring duration: [N] days
   - Explain: "I will check prices automatically and purchase for you when conditions are met, without asking again."
   - Ask: "Ready to set this up? I'll need your biometric authorization."
   - Wait for user confirmation (Yes, Confirm, Go ahead, etc.)

4. **Create Intent Mandate & Request Signature (Immediately)**
   - Once user confirms, you MUST do BOTH steps in sequence WITHOUT waiting:
   - Step A: Call `create_hnp_intent` tool → receive Intent JSON
   - Step B: IMMEDIATELY call `request_user_intent_signature` with that Intent JSON
   - DO NOT wait for another user message between these steps!
   - DO NOT ask "shall I proceed?" - just do it!

5. **After Triggering Signature Request**
   - Explain: "Please approve this in the biometric modal that will appear."
   - Include orange warning: "You are pre-authorizing autonomous purchase. I will buy automatically when conditions are met without asking you again."
   - IMPORTANT: The signature is NOT applied immediately - user must click Confirm in the modal
   - Wait for user to return saying "I signed it" or "Done" before proceeding to step 6

6. **Activate Monitoring** (ONLY After user confirms they signed)
   - ONLY call `activate_monitoring_job` tool AFTER user confirms they completed signature
   - User will say "I signed it" or similar after completing the modal
   - Then use `activate_monitoring_job` tool to start background monitoring
   - Explain what happens next:
     * "Monitoring activated! I'll check every [X] minutes."
     * "Current price: $[Y]"
     * "I'll purchase automatically when price drops to $[Z] or below AND delivery is [N] days or less."
     * "Monitoring expires in [M] days."
     * "You can cancel anytime using the monitoring card."

**Available Tools:**
- `extract_monitoring_constraints(user_query)` - Parse constraints from natural language
- `search_products(query, max_price)` - Search product catalog to validate product exists
- `create_hnp_intent(user_id, product_query, max_price_cents, max_delivery_days, duration_days)` - Create Intent mandate
- `request_user_intent_signature(user_id, intent_mandate_id, intent_summary, intent_mandate_json)` - Request pre-authorization signature (pass Intent JSON from create_hnp_intent)
- `activate_monitoring_job(user_id, signed_intent_mandate)` - Start background monitoring

**Important Rules:**
1. ALWAYS extract constraints first - don't assume user wants default values
2. BE EXPLICIT about autonomous behavior - user must understand what they're authorizing
3. After user confirms setup, IMMEDIATELY call both tools in sequence:
   - First: `create_hnp_intent`
   - Second: `request_user_intent_signature` (with the Intent JSON from step 1)
   - DO NOT wait between these two calls!
4. DO NOT activate monitoring until user confirms they signed
5. Validate product exists before creating Intent (use search_products)
6. If conditions are ALREADY MET at setup time, inform user but still create monitoring
7. Default to 7 days monitoring duration unless user specifies otherwise
8. Explain check frequency (30 seconds in demo mode, 5 min in production)
9. Celebrate when monitoring is activated!

**CORRECT FLOW EXAMPLE:**

User: "Monitor coffee maker under $50"
You: [Extract constraints, search product, present summary]
You: "Shall I set up this monitoring?"

User: "Yes"
You: [Call create_hnp_intent tool, receive Intent JSON]
You: [IMMEDIATELY call request_user_intent_signature tool with the Intent JSON - DO NOT WAIT!]
You: "Please approve this in the biometric modal. This authorizes autonomous purchase."
[WAIT for user to complete modal]

User: "I signed it" or "Done"
You: [Call activate_monitoring_job tool]
You: "Monitoring activated! I'll check every 5 minutes..."

**Constraint Extraction Examples:**

"Buy AirPods if price drops below 180"
→ product_query: "Apple AirPods Pro"
→ max_price_cents: 18000
→ max_delivery_days: 7 (default if not specified)
→ duration_days: 7 (default)

"Let me know when coffee maker is under $70 and can ship in 2 days"
→ product_query: "coffee maker"
→ max_price_cents: 7000
→ max_delivery_days: 2
→ duration_days: 7

"Monitor laptop deals under $800 for next 14 days"
→ product_query: "laptop"
→ max_price_cents: 80000
→ max_delivery_days: 7 (default)
→ duration_days: 14

**AP2 Protocol Context (HNP Flow):**
- Intent Mandate MUST be signed by user (pre-authorization per AP2)
- Intent contains constraints that Cart cannot exceed
- Background monitoring checks conditions every N minutes
- When conditions met: Agent creates Cart (agent-signed, NOT user-signed)
- Cart must reference Intent ID (mandate chain per AP2)
- Payment Agent validates Cart does not exceed Intent constraints
- human_not_present flag set in Payment mandate

**Edge Cases:**

**Product out of stock:**
- Continue monitoring both price AND availability
- When both conditions met, trigger purchase

**Conditions never met:**
- When Intent expires after monitoring duration, notify user
- Show final check results
- Offer to set up new monitoring

**Conditions already met at setup:**
- Inform user: "Great news! Conditions are already met (price $X, delivery Y days)."
- Still create monitoring in case they change
- Or offer: "Would you like me to purchase immediately instead?"

**User wants to cancel:**
- Monitoring card in frontend has "Cancel Monitoring" button
- When cancelled, deactivate job, preserve Intent for history

**Clarifying Questions:**
- "What's your maximum price?"
- "How quickly do you need it delivered?"
- "How long should I monitor? (Default is 7 days)"
- "Which model of [product] did you have in mind?"

**Conversational Tone:**
- Enthusiastic about helping user save money
- Clear about autonomous behavior (don't hide it!)
- Patient with clarifications
- Celebrate successful monitoring setup
- Sympathetic if conditions not met by expiration

Remember: You are enabling AUTONOMOUS purchase with user PRE-AUTHORIZATION. Be crystal clear about this!
"""


# ============================================================================
# Tool Definitions
# ============================================================================

@tool
def extract_monitoring_constraints(user_query: str) -> Dict[str, Any]:
    """
    Extract monitoring constraints from user's natural language query.

    Args:
        user_query: User's request (e.g., "Buy AirPods if price drops below $180")

    Returns:
        Dictionary with product_query, max_price_cents, max_delivery_days, duration_days

    Examples:
        "Buy AirPods if price below 180" → {"product": "AirPods", "max_price": 18000, "max_delivery": 7, "duration": 7}
    """
    # This is a simple parser - in production would use more sophisticated NLP
    constraints = {
        "product_query": "",
        "max_price_cents": None,
        "max_delivery_days": 7,  # Default
        "duration_days": 7  # Default monitoring duration
    }

    query_lower = user_query.lower()

    # Extract product (everything before "if" or "when")
    if " if " in query_lower:
        product_part = query_lower.split(" if ")[0]
    elif " when " in query_lower:
        product_part = query_lower.split(" when ")[0]
    else:
        product_part = query_lower

    # Clean up product query
    product_part = product_part.replace("buy ", "").replace("purchase ", "").replace("get ", "")
    product_part = product_part.replace("me ", "").strip()
    constraints["product_query"] = product_part

    # Extract price
    import re
    price_match = re.search(r'\$?(\d+)', user_query)
    if price_match:
        price_dollars = int(price_match.group(1))
        constraints["max_price_cents"] = price_dollars * 100

    # Extract delivery days
    delivery_match = re.search(r'(\d+)\s*day', user_query.lower())
    if delivery_match:
        constraints["max_delivery_days"] = int(delivery_match.group(1))

    # Extract duration
    duration_match = re.search(r'(\d+)\s*day', user_query.lower())
    if duration_match and "for" in query_lower:
        constraints["duration_days"] = int(duration_match.group(1))

    logger.info(f"Extracted constraints: {constraints}")
    return constraints


# ============================================================================
# Agent Factory
# ============================================================================

def create_hnp_delegate_agent(
    search_products_func,
    create_intent_func,
    request_signature_func,
    activate_monitoring_func,
    sse_emit_fn=None
) -> Agent:
    """
    Create HNP Delegate Agent with tools injected.

    Args:
        search_products_func: Function to search product catalog
        create_intent_func: Function to create Intent mandate
        request_signature_func: Function to request user signature
        activate_monitoring_func: Function to activate monitoring job
        sse_emit_fn: Optional SSE event emitter for custom events

    Returns:
        Configured Strands Agent
    """
    from ..config import settings

    # Create Bedrock model
    bedrock_model = BedrockModel(
        model_id=settings.aws_bedrock_model_id,
        region_name=settings.aws_region,
        temperature=0.7,
        streaming=True
    )

    # Wrap external functions as tools
    @tool
    def search_products(query: str, max_price: Optional[float] = None) -> str:
        """
        Search product catalog by query and optional max price.

        Args:
            query: Search terms
            max_price: Maximum price in dollars

        Returns:
            JSON string of matching products with id, name, price_cents, stock, delivery
        """
        results = search_products_func(query, max_price)
        return json.dumps(results, indent=2)

    @tool
    def create_hnp_intent(
        user_id: str,
        product_query: str,
        max_price_cents: int,
        max_delivery_days: int = 7,
        duration_days: int = 7
    ) -> str:
        """
        Create Intent mandate for HNP monitoring.

        Args:
            user_id: User identifier
            product_query: Product search query
            max_price_cents: Maximum price in cents
            max_delivery_days: Maximum delivery time in days
            duration_days: How long to monitor (default 7 days)

        Returns:
            JSON string of Intent mandate
        """
        result = create_intent_func(
            user_id=user_id,
            product_query=product_query,
            max_price_cents=max_price_cents,
            max_delivery_days=max_delivery_days,
            duration_days=duration_days
        )
        return json.dumps(result, indent=2)

    @tool
    def request_user_intent_signature(
        user_id: str,
        intent_mandate_id: str,
        intent_summary: str,
        intent_mandate_json: str
    ) -> str:
        """
        Request user to sign Intent mandate (pre-authorization).

        Args:
            user_id: User identifier
            intent_mandate_id: Intent mandate ID to sign
            intent_summary: Human-readable summary for modal
            intent_mandate_json: JSON string of Intent mandate from create_hnp_intent

        Returns:
            JSON with signature_required=true to trigger frontend modal
        """
        # Parse Intent mandate
        intent_mandate = json.loads(intent_mandate_json) if isinstance(intent_mandate_json, str) else intent_mandate_json

        result = request_signature_func(
            user_id=user_id,
            mandate_id=intent_mandate_id,
            mandate_type="intent",
            summary=intent_summary,
            hnp_warning=True,
            mandate_data=intent_mandate
        )

        # Get the Intent mandate data from result
        intent_mandate = result.get("mandate_data", intent_mandate)

        # Emit SSE event to trigger frontend signature modal
        if sse_emit_fn:
            logger.info(f"Emitting signature_requested SSE event for Intent {intent_mandate_id}")
            sse_emit_fn("signature_requested", {
                "mandate_id": intent_mandate_id,
                "mandate_type": "intent",
                "summary": intent_summary,
                "user_id": user_id,
                "hnp_warning": True,
                "mandate_data": intent_mandate  # Include Intent data for signing
            })

        return json.dumps(result, indent=2)

    @tool
    def activate_monitoring_job(
        user_id: str,
        signed_intent_mandate: str
    ) -> str:
        """
        Activate background monitoring job after Intent is signed.

        Args:
            user_id: User identifier
            signed_intent_mandate: JSON string of signed Intent mandate

        Returns:
            JSON with job details (job_id, check_interval, expires_at)
        """
        intent_dict = json.loads(signed_intent_mandate) if isinstance(signed_intent_mandate, str) else signed_intent_mandate
        result = activate_monitoring_func(
            user_id=user_id,
            intent_mandate=intent_dict
        )
        return json.dumps(result, indent=2)

    # Create agent with all tools
    agent = Agent(
        model=bedrock_model,
        tools=[
            extract_monitoring_constraints,
            search_products,
            create_hnp_intent,
            request_user_intent_signature,
            activate_monitoring_job
        ],
        system_prompt=HNP_DELEGATE_SYSTEM_PROMPT
    )

    logger.info("HNP Delegate Agent created with Strands SDK")
    return agent
