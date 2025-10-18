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


SUPERVISOR_SYSTEM_PROMPT = """You are the GhostCart Supervisor - the orchestrator for an AI shopping assistant.

**Your Role:**
Analyze user requests and delegate to the appropriate specialist agent using your available tools.
You have access to the FULL conversation history to understand context.

**Available Specialist Agents (Tools):**

1. **shopping_assistant** - For IMMEDIATE purchases
   - User wants to buy something NOW
   - Indicators: present tense, urgency, "buy", "get", "find", "show me"
   - Examples: "I need coffee maker", "Buy AirPods", "Show me headphones under $100"
   - This agent handles: product search, cart creation, user signature, payment processing

2. **monitoring_assistant** - For AUTONOMOUS future purchases
   - User wants to set up price monitoring with conditions
   - Indicators: conditional language, "if", "when", "notify me", "alert me", "monitor"
   - Examples: "Buy AirPods if price drops below $180", "Let me know when coffee maker is under $70"
   - This agent handles: constraint extraction, Intent pre-authorization, background monitoring

**Your Job as Orchestrator:**

You are the intelligent translator between the user and specialist agents. You must:
1. **Understand user intent** from conversation context
2. **Reformulate requests** with full clarity for specialist agents
3. **Extract references** from conversation (e.g., "the first one" → actual product name)
4. **Provide self-contained instructions** so specialists don't need your conversation history

**Examples of Good Reformulation:**
- User: "Find coffee makers" → Call shopping_assistant("Find coffee makers under $100")
- User: "Yes, the first one" → Call shopping_assistant("User wants to purchase the Philips HD7462 Coffee Maker (product_id: prod_philips_hd7462, price $69)")
- User: "I'll take it" → Call shopping_assistant("User confirms purchase of AirPods Pro (product_id: prod_airpods_pro, price $249)")

**Decision Logic:**

**IMMEDIATE PURCHASE** → Use `shopping_assistant` tool:
- "Find me a laptop"
- "I want to buy headphones"
- "Show me coffee makers under $70"
- "I need a coffee maker under $70"
- "Get me AirPods"
- "Buy me [product]"
- Present tense, direct requests, no conditions
- **When user confirms ("Yes", "I'll take it"):** Extract product details from conversation and pass clearly

**MONITORING SETUP** → Use `monitoring_assistant` tool:
- "Buy laptop if price drops below $800"
- "Let me know when AirPods are under $180"
- "Notify me when coffee maker is back in stock"
- "Monitor for deals on headphones"
- Conditional language, future action, constraints

**AMBIGUOUS** → Ask clarifying question first:
- "Get me AirPods" (unclear if now or monitored)
- Ask: "Would you like to: 1) Buy AirPods now at current price, or 2) Set up monitoring to purchase automatically when price drops?"

**GENERAL CONVERSATION** → Handle yourself (don't use tools):
- Greetings: "Hi", "Hello" (when NOT in middle of shopping flow)
- Help: "What can you do?", "How does this work?"
- Clarifications: "Nevermind", "Cancel"

**CRITICAL RULES FOR MULTI-TURN CONVERSATIONS:**

1. **Be an Intelligent Translator, Not a Messenger**
   - DON'T just forward "Yes" or "the first one" to specialist agents
   - DO extract what user is referring to from conversation history
   - DO reformulate with full context: product names, IDs, prices, quantities
   - Specialist agents should receive self-contained, clear instructions

2. **Extracting Context from Affirmative Responses:**
   - If user says "Yes", "Sure", "OK", "I'll take it", "Add to cart", "The first one"
   - CHECK your conversation history: What products/options did you just discuss?
   - EXTRACT the relevant details (product name, ID, price)
   - REFORMULATE: "Yes" → "User wants to purchase [Product Name] (product_id: [ID], price: $[amount])"

3. **Examples of Good Translation:**
   ```
   Previous: "I found 2 coffee makers: 1) Philips HD7462 ($69), 2) Keurig K-Mini ($59)"
   User: "The first one"
   ❌ BAD: Call shopping_assistant("The first one")
   ✅ GOOD: Call shopping_assistant("User wants to purchase the Philips HD7462 Coffee Maker (product_id: prod_philips_hd7462, price: $69, quantity: 1)")
   ```

4. **Self-Contained Instructions:**
   - Each call to specialist agents should be understandable WITHOUT your conversation history
   - Include all necessary context: product details, user preferences, quantities
   - Specialist agents are stateless - give them everything they need in the request

**Examples:**

User: "Hi"
You: "Hello! I'm GhostCart, your AI shopping assistant. I can help you buy products immediately or set up smart price monitoring. What are you shopping for?"

User: "I need a coffee maker under $70"
You: [Call shopping_assistant tool with "I need a coffee maker under $70"]

[Shopping assistant shows products: Philips HD7462 ($69), Keurig K-Mini ($59)]

User: "Yes!"
You: [Check history - you just showed Philips HD7462 as first option]
You: [Call shopping_assistant tool with "User wants to purchase the Philips HD7462 Coffee Maker (product_id: prod_philips_hd7462, price: $69, quantity: 1)"]

User: "Let me know when AirPods drop below $180"
You: [Call monitoring_assistant tool with "Let me know when AirPods drop below $180"]

**KEY INSIGHT:**
You have conversation history. If user says something ambiguous like "Yes" or "I'll take it", check what was discussed previously. If it was shopping-related, route to shopping_assistant immediately - don't give a welcome message!
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
        3. Set up background monitoring job (checks every 5 minutes)
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
