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


HNP_DELEGATE_SYSTEM_PROMPT = """You are GhostCart's monitoring specialist - help users set up intelligent price tracking with pre-authorized automatic purchases through natural conversation.

## Your Role

You're an intelligent monitoring assistant with tools to extract constraints, validate products, create monitoring Intents, request pre-authorization, and activate background monitoring. Guide users from constraint definition to active monitoring naturally, not as a scripted bot. This is powerful - users pre-authorize autonomous purchases that happen automatically without further confirmation.

## Tools Available

- `extract_monitoring_constraints(user_query)` - Parse price/delivery constraints from natural language
- `search_products(query, max_price)` - Find products by keyword
- `create_hnp_intent(product_query, max_price_cents, max_delivery_days, duration_days)` - Create monitoring Intent
- `request_user_intent_signature(intent_id, summary, intent_json)` - Request pre-authorization signature
- `get_signed_intent_mandate(intent_mandate_id)` - Retrieve signed Intent after approval
- `activate_monitoring_job(signed_intent_mandate)` - Start background monitoring job

## Critical System Behaviors

**Constraint extraction first**: Use `extract_monitoring_constraints` to parse the user's request into structured constraints (max_price_cents, max_delivery_days). Validate the extraction makes sense before proceeding.

**Product search validates availability**: The `search_products` function returns matching products. If current prices don't meet the threshold, that's expected - monitoring will catch price drops later. Use search to confirm the product exists in our catalog.

**Autonomous purchase warning - ALWAYS**: Users must understand this will purchase automatically when conditions are met. Always include clear warnings: "⚠️ This will purchase automatically when price drops - no further confirmation needed." This is critical for informed consent.

**Authorization requires waiting**: After calling `request_user_intent_signature()`, you must wait for the user's explicit confirmation before activating monitoring. The user will respond with: "I have signed the Intent mandate (ID: intent_hnp_...)." Do not activate monitoring until you receive this specific message.

**Immediate Intent creation after validation**: After extracting constraints and validating the product exists, proceed directly to creating the Intent and requesting signature. Don't wait for additional user confirmation - the signature modal IS the confirmation mechanism.

**Mandatory activation after signature**: When user confirms they signed the Intent, you must call both `get_signed_intent_mandate()` and `activate_monitoring_job()` to actually start the background monitoring. Don't just acknowledge - use the tools to activate monitoring.

**Error handling**: If a tool call fails, explain the issue clearly and suggest next steps. Don't silently fail or retry without user input.

## Example Flow

User: "Monitor for Dyson vacuum under $550"
You: `extract_monitoring_constraints(...)` → `search_products("Dyson vacuum", 550)` → `create_hnp_intent(...)` → `request_user_intent_signature(...)` → "I found Dyson V11 at $599.99. I'll monitor and purchase automatically when it drops to $550 or below with delivery in 7 days. ⚠️ This will purchase without further confirmation. Please approve in the modal."

User: "I have signed the Intent mandate (ID: intent_hnp_abc123)."
You: `get_signed_intent_mandate("intent_hnp_abc123")` → `activate_monitoring_job(signed_intent)` → "✅ Monitoring activated! Checking every 10 seconds. When Dyson drops to $550 or below, I'll purchase automatically and notify you."

## Conversation Style

Be helpful, concise, and adapt your tone to the user. Always emphasize the autonomous nature to ensure users understand what they're pre-authorizing. Trust your judgment to create a smooth monitoring experience.
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
    get_signed_mandate_fn=None,
    sse_emit_fn=None,
    user_id=None  # Add user_id context
) -> Agent:
    """
    Create HNP Delegate Agent with tools injected.

    Args:
        search_products_func: Function to search product catalog
        create_intent_func: Function to create Intent mandate
        request_signature_func: Function to request user signature
        activate_monitoring_func: Function to activate monitoring job
        get_signed_mandate_fn: Optional function to retrieve signed Intent from database
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
    async def create_hnp_intent(
        product_query: str,
        max_price_cents: int,
        max_delivery_days: int = 7,
        duration_days: int = 7
    ) -> str:
        """
        Create Intent mandate for HNP monitoring and save to database.

        The user_id is automatically provided from the request context.

        Args:
            product_query: Product search query (e.g., "Dyson vacuum")
            max_price_cents: Maximum price willing to pay in cents (e.g., 55000 for $550)
            max_delivery_days: Maximum acceptable delivery time in days (default: 7)
            duration_days: How long to monitor for price drops in days (default: 7)

        Returns:
            JSON string of Intent mandate with auto-generated mandate_id field
            Example: {"mandate_id": "intent_hnp_a1b2c3d4e5f6g7h8", "user_id": "...", ...}
        """
        try:
            # Use user_id from context (passed when agent created)
            actual_user_id = user_id or "user_demo_001"

            result = await create_intent_func(
                user_id=actual_user_id,
                product_query=product_query,
                max_price_cents=max_price_cents,
                max_delivery_days=max_delivery_days,
                duration_days=duration_days
            )
            logger.info(f"Created Intent mandate: {result.get('mandate_id', 'unknown')}")
            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Failed to create Intent mandate: {e}", exc_info=True)
            return json.dumps({
                "error": f"Failed to create Intent: {str(e)}",
                "error_type": type(e).__name__
            })

    @tool
    def request_user_intent_signature(
        intent_mandate_id: str,
        intent_summary: str,
        intent_mandate_json: str
    ) -> str:
        """
        Request user to sign Intent mandate (pre-authorization).

        The user_id is automatically provided from the request context.

        Args:
            intent_mandate_id: Intent mandate ID to sign (extract from create_hnp_intent response)
            intent_summary: Human-readable summary (e.g., "Dyson vacuum ≤$550, delivery ≤7 days")
            intent_mandate_json: Full Intent JSON from create_hnp_intent tool

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
    async def get_signed_intent_mandate(intent_mandate_id: str) -> str:
        """
        Retrieve a signed Intent mandate from the database.

        Use this tool when user says they have signed the Intent to retrieve
        the signed Intent data before activating monitoring.

        IMPORTANT: The frontend confirmation message contains the exact Intent ID.
        Extract it from the message: "I have signed the Intent mandate (ID: intent_hnp_...)."

        Args:
            intent_mandate_id: The mandate_id of the Intent (e.g., "intent_hnp_...")

        Returns:
            JSON string of the signed Intent mandate with signature
            OR JSON with "error" field if retrieval fails
        """
        if not get_signed_mandate_fn:
            return json.dumps({
                "error": "Intent retrieval function not configured"
            })

        try:
            signed_intent = await get_signed_mandate_fn(intent_mandate_id)
            logger.info(f"Retrieved signed Intent: {intent_mandate_id}")
            return json.dumps(signed_intent)
        except Exception as e:
            logger.error(f"Failed to retrieve signed Intent {intent_mandate_id}: {e}", exc_info=True)
            return json.dumps({
                "error": "Could not find signed Intent in database. This might mean the signature process failed or the Intent wasn't saved properly.",
                "error_type": type(e).__name__,
                "intent_id": intent_mandate_id
            })

    @tool
    async def activate_monitoring_job(
        signed_intent_mandate: str
    ) -> str:
        """
        Activate background monitoring job after Intent is signed.

        The user_id is automatically provided from the request context.

        Args:
            signed_intent_mandate: JSON string of signed Intent mandate

        Returns:
            JSON with job details (job_id, check_interval, expires_at)
        """
        try:
            intent_dict = json.loads(signed_intent_mandate) if isinstance(signed_intent_mandate, str) else signed_intent_mandate

            # Use user_id from context (passed when agent created)
            actual_user_id = user_id or "user_demo_001"

            logger.info(f"Activating monitoring job for user {actual_user_id}, intent {intent_dict.get('mandate_id')}")

            result = await activate_monitoring_func(
                user_id=actual_user_id,
                intent_mandate=intent_dict
            )

            logger.info(f"Monitoring activation successful: {result.get('job_id')}")

            # Emit SSE event to notify frontend that monitoring is now active
            if sse_emit_fn:
                sse_emit_fn("monitoring_activated", {
                    "job_id": result.get('job_id'),
                    "intent_id": intent_dict.get('mandate_id'),
                    "user_id": user_id,
                    "message": "Monitoring job activated successfully"
                })
                logger.info(f"Emitted monitoring_activated SSE event for job {result.get('job_id')}")

            return json.dumps(result, indent=2)
        except Exception as e:
            logger.error(f"Failed to activate monitoring: {e}", exc_info=True)
            return json.dumps({
                "error": str(e),
                "error_type": type(e).__name__,
                "success": False
            }, indent=2)

    # Create agent with all tools
    agent = Agent(
        model=bedrock_model,
        tools=[
            extract_monitoring_constraints,
            search_products,
            create_hnp_intent,
            request_user_intent_signature,
            get_signed_intent_mandate,
            activate_monitoring_job
        ],
        system_prompt=HNP_DELEGATE_SYSTEM_PROMPT
    )

    logger.info("HNP Delegate Agent created with Strands SDK")
    return agent
