"""
Supervisor Agent - Orchestrator Using Agents-as-Tools Pattern

The Supervisor is the ENTRY POINT for all user interactions.
It uses LLM reasoning to route requests to specialized agents.

Architecture (per Strands SDK):
- Supervisor Agent has specialist agents as tools (@tool decorator)
- LLM analyzes user intent and calls appropriate specialist agent tool
- Specialist agents (HP Shopping, HNP Delegate) handle domain logic
- Supervisor never executes domain logic itself - only orchestrates

AP2 Protocol Context:
- Entry point for chat endpoint
- Routes to HP Shopping Agent for immediate purchases
- Routes to HNP Delegate Agent for monitoring setup
- Handles general conversation directly (greetings, help)
"""
from typing import Optional, Callable, Dict, Any
from strands import Agent, tool
from strands.models import BedrockModel
from strands.session import SessionManager
import logging

logger = logging.getLogger(__name__)


SUPERVISOR_SYSTEM_PROMPT = """You are GhostCart's conversational AI supervisor - a smart orchestrator that routes user requests to specialized shopping agents.

## Core Capabilities

You coordinate two specialist agents:

**shopping_assistant** - Handles immediate purchases
- Product search, cart creation, payment processing
- Use when user wants to buy something now

**monitoring_assistant** - Handles autonomous price monitoring
- Sets up conditional purchases with pre-authorization
- Use when user wants to buy later based on price/availability conditions

## Your Intelligence

You're a **contextual interpreter**, not a simple router. Use your conversation history to:

- Understand implicit references ("yes", "the first one", "that product")
- Distinguish between immediate vs conditional purchase intent
- Resolve ambiguity through clarification when needed
- Translate vague user statements into clear, actionable requests

## Routing Decision Framework

**Route to shopping_assistant when:**
- User expresses immediate intent (browsing, selecting, buying now)
- User confirms a product selection in an active shopping flow
- Language is present-tense or urgent

**Route to monitoring_assistant when:**
- User specifies conditions (price thresholds, availability triggers)
- Language includes "if", "when", "notify me", "alert me", "monitor"
- User wants automated future purchase

**Handle directly when:**
- Greeting or general conversation outside an active flow
- Requests for help or explanation
- Ambiguous intent requiring clarification

## Context Translation

When routing to specialists, **reformulate ambiguous user input** with concrete details extracted from conversation history:

- "Yes" → "User confirms purchase of [Product Name] (ID: [product_id], price: $[amount])"
- "The second one" → "User selects [Product Name] from the search results"
- "I'll take it" → "User approves [Product Name] at $[price] with [delivery info]"

Specialists are stateless - give them complete, self-contained instructions so they don't need your conversation context.

## Conversation Style

Be natural, helpful, and concise. You're a smart assistant, not a script. Adapt your responses based on context - don't repeat greetings mid-conversation or ignore active shopping flows.

## Examples

**Immediate purchase:**
User: "Find headphones under $100"
→ Route to shopping_assistant("Find headphones under $100")

**Contextual confirmation:**
[After showing product options]
User: "The first one"
→ Route to shopping_assistant("User wants to purchase [Product Name] (product_id: [ID], price: $[amount], quantity: 1)")

**Conditional purchase:**
User: "Buy AirPods if they drop below $180"
→ Route to monitoring_assistant("Buy AirPods if they drop below $180")

**Ambiguous intent:**
User: "Get me AirPods"
→ Clarify: "Would you like to buy AirPods now at the current price, or set up monitoring to purchase when the price drops?"

Trust your intelligence. Adapt to the conversation. Route smartly.
"""


def create_supervisor_agent(
    hp_shopping_agent: Agent,
    hnp_delegate_agent: Optional[Agent] = None,
    model_id: Optional[str] = None,
    region_name: Optional[str] = None,
    session_manager: Optional[SessionManager] = None,
    event_queue: Optional[Any] = None
) -> Agent:
    """
    Create Supervisor Agent using agents-as-tools pattern with Strands context management.

    The Supervisor orchestrates by routing user requests to specialist agents.
    Per Strands SDK best practice: specialists are wrapped as @tool decorated functions.

    Context Management (Option A - Supervisor Only):
    - ONLY Supervisor has SessionManager for conversation persistence
    - Specialist agents (HP Shopping, HNP Delegate) are STATELESS
    - Supervisor passes its FULL conversation history to specialist agents when calling them
    - This gives specialists complete context without needing their own SessionManager
    - Simpler architecture: one source of truth for conversation state

    Args:
        hp_shopping_agent: Strands Agent for immediate purchases (human-present flow)
        hnp_delegate_agent: Strands Agent for monitoring setup (human-not-present flow)
        model_id: Bedrock model ID (defaults to settings)
        region_name: AWS region (defaults to settings)
        session_manager: SessionManager for persisting conversation state (NEW)
        event_queue: Queue for custom tool events (product_results, cart_created, etc.)

    Returns:
        Supervisor Agent with specialist agents as callable tools and automatic context management

    Architecture:
        User Message → Supervisor (LLM analyzes intent)
                    ↓
        Supervisor calls shopping_assistant tool OR monitoring_assistant tool
                    ↓
        Specialist agent handles complete flow (with automatic context from session)
                    ↓
        Result returns to Supervisor → User

    AP2 Protocol:
        - Supervisor is entry point (FR-025: orchestrates, never executes domain logic)
        - HP Shopping Agent for immediate purchase (FR-026, FR-030)
        - HNP Delegate Agent for monitoring (FR-027, FR-031)
        - LLM-based routing, not keywords (FR-029)

    Context Flow:
        - Session created with FileSessionManager(session_id) or S3SessionManager(session_id)
        - Supervisor agent loads conversation history via session_manager
        - When Supervisor calls specialist tool, it passes its full message history
        - Specialist receives complete context from Supervisor's history
        - Supervisor saves updated history after completion
    """
    from ..config import settings

    # Store reference to supervisor agent (will be set after agent creation)
    supervisor_agent_ref = {'agent': None}

    # Wrap HP Shopping Agent as tool (agents-as-tools pattern per Strands docs)
    @tool
    async def shopping_assistant(user_request: str) -> str:
        """
        Handle immediate purchase requests (human-present flow).

        USE THIS TOOL when user wants to buy something NOW or browse products.

        Trigger phrases:
        - "I need [product]"
        - "Find me [product]"
        - "Show me [product]"
        - "I want [product]"
        - "Buy [product]"
        - "Get me [product]"
        - Any mention of a specific product category or name

        Examples that REQUIRE this tool:
        - "Find coffee maker" → Call this tool
        - "I need a coffee maker under $70" → Call this tool
        - "Buy AirPods" → Call this tool
        - "Show me laptops under $800" → Call this tool

        This specialist agent will:
        1. Search products based on user query
        2. Present options to user
        3. Create cart when user selects product
        4. Request user signature for authorization
        5. Process payment via Payment Agent

        Args:
            user_request: The user's complete shopping request (pass the full message)

        Returns:
            Response from shopping agent about search results, cart, or payment status
        """
        logger.info(f"Supervisor routing to HP Shopping Agent: {user_request[:50]}...")
        try:
            # Supervisor has already reformulated user_request with full context
            # HP agent is STATELESS - it receives self-contained, clear instructions
            # No need to pass Supervisor's message history - avoids tool_use/tool_result mismatch
            logger.info(f"Passing reformulated request to HP Shopping Agent: {user_request[:100]}...")

            # Stream from nested HP Shopping Agent with reformulated request only
            full_response = ""
            final_result = None

            async for event in hp_shopping_agent.stream_async(user_request):
                # Capture text chunks
                if "data" in event:
                    chunk = event["data"]
                    full_response += chunk

                # Capture final result
                if "result" in event:
                    final_result = event["result"]

            # Extract response from result
            if final_result:
                if hasattr(final_result, 'message'):
                    msg = final_result.message
                    if isinstance(msg, dict) and 'content' in msg:
                        content = msg['content']
                        if isinstance(content, list) and len(content) > 0:
                            full_response = content[0].get('text', str(msg))
                        else:
                            full_response = str(content)
                    else:
                        full_response = str(msg)

            return full_response if full_response else "HP Shopping Agent completed."
        except Exception as e:
            logger.error(f"HP Shopping Agent error: {e}")
            return f"I encountered an error while searching for products: {str(e)}"

    # Wrap HNP Delegate Agent as tool (agents-as-tools pattern per Strands docs)
    @tool
    async def monitoring_assistant(user_request: str) -> str:
        """
        Handle monitoring setup requests (human-not-present flow).

        Use this when user wants to set up AUTOMATED future purchase with conditions.
        Examples: "Buy if price drops below $X", "Notify me when available", "Monitor for deals"

        This agent will:
        1. Extract price/delivery constraints from user request
        2. Create Intent mandate requiring user pre-authorization signature
        3. Set up background monitoring job (configurable)
        4. Automatically purchase when conditions met
        5. Notify user of autonomous purchase

        Args:
            user_request: The user's monitoring request (full message)

        Returns:
            Response about monitoring setup, constraints, and pre-authorization requirements
        """
        if hnp_delegate_agent is None:
            return "Monitoring setup is not yet available. Please try immediate purchase instead, or check back later."

        logger.info(f"Supervisor routing to HNP Delegate Agent: {user_request[:50]}...")
        try:
            # Supervisor has already reformulated user_request with full context
            # HNP agent is STATELESS - it receives self-contained, clear instructions
            # No need to pass Supervisor's message history - avoids tool_use/tool_result mismatch
            logger.info(f"Passing reformulated request to HNP Delegate Agent: {user_request[:100]}...")

            # Stream from nested HNP Delegate Agent with reformulated request only
            full_response = ""
            final_result = None

            async for event in hnp_delegate_agent.stream_async(user_request):
                # Capture text chunks
                if "data" in event:
                    chunk = event["data"]
                    full_response += chunk

                # Capture final result
                if "result" in event:
                    final_result = event["result"]

            # Extract response from result
            if final_result:
                if hasattr(final_result, 'message'):
                    msg = final_result.message
                    if isinstance(msg, dict) and 'content' in msg:
                        content = msg['content']
                        if isinstance(content, list) and len(content) > 0:
                            full_response = content[0].get('text', str(msg))
                        else:
                            full_response = str(content)
                    else:
                        full_response = str(msg)

            return full_response if full_response else "HNP Delegate Agent completed."
        except Exception as e:
            logger.error(f"HNP Delegate Agent error: {e}")
            return f"I encountered an error setting up monitoring: {str(e)}"

    # Create Bedrock model
    bedrock_model = BedrockModel(
        model_id=model_id or settings.aws_bedrock_model_id,
        region_name=region_name or settings.aws_region,
        temperature=0.7
    )

    # Create Supervisor Agent with Strands context management
    agent = Agent(
        model=bedrock_model,
        tools=[shopping_assistant, monitoring_assistant],
        system_prompt=SUPERVISOR_SYSTEM_PROMPT,
        session_manager=session_manager  # Persists state across requests (includes conversation management)
    )

    # Set agent reference so tool functions can access supervisor's messages
    supervisor_agent_ref['agent'] = agent

    logger.info(
        "Supervisor Agent created with specialist agents as tools (agents-as-tools pattern) "
        f"and session management (session_manager={'enabled' if session_manager else 'disabled'})"
    )

    return agent
