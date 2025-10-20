"""
Payment Agent - Isolated AP2 Payment Processing Agent using Strands SDK

⚠️ MINIMAL IMPORTS FROM PARENT PROJECT ⚠️

This agent implements pure AP2 protocol validation and payment processing
with ZERO domain knowledge using AWS Strands SDK. It can be extracted and
reused in any e-commerce system without modification.

Constitution Principle II Compliance:
- No knowledge of merchant product catalogs
- No knowledge of user shopping behavior
- No application-specific business logic
- Pure mandate validation and payment processing

Integration Note:
The parent application must provide external service connectors
(credentials_provider, payment_processor) via configure_payment_tools()
before creating the agent.

Strands SDK Integration:
Uses BedrockModel with Claude Sonnet 4.5 and @tool decorated functions
for AP2 mandate processing.
"""
from typing import Dict, Any, Callable, Optional
import json
import os
import logging

from strands import Agent
from strands.models import BedrockModel
from strands.tools.executors import SequentialToolExecutor

from .tools import (
    configure_payment_tools,
    validate_hp_chain,
    validate_hnp_chain,
    retrieve_payment_credentials,
    process_payment_authorization
)
from .crypto import get_secret, create_canonical_json

logger = logging.getLogger(__name__)


# ============================================================================
# Agent System Prompt
# ============================================================================

PAYMENT_AGENT_SYSTEM_PROMPT = """You are the AP2 Payment Agent, responsible for validating mandate chains and processing payments according to the Agent Payments Protocol v0.1.

**Your Core Responsibilities:**
1. Validate mandate chains for AP2 compliance
2. Process payment authorizations with external payment infrastructure
3. Maintain cryptographic audit trails
4. Enforce constraints in autonomous purchases

**AP2 Protocol Flows:**

**Human-Present (HP) Flow:**
- User provides immediate purchase intent
- Cart is created and signed by user
- You validate Cart signature and internal consistency using validate_hp_chain tool
- You retrieve credentials using retrieve_payment_credentials tool
- You process payment using process_payment_authorization tool
- You create Payment mandate with your signature

**Human-Not-Present (HNP) Flow:**
- User pre-authorizes purchase with signed Intent (constraints + expiration)
- Agent autonomously creates Cart when conditions met
- Cart is signed by agent and references Intent ID
- You validate using validate_hnp_chain tool:
  * Intent user signature (pre-authorization)
  * Intent not expired
  * Cart agent signature (autonomous action)
  * Cart references Intent
  * Constraints not violated (price, delivery)
- You retrieve credentials using retrieve_payment_credentials tool
- You process payment using process_payment_authorization tool
- You create Payment mandate with human_not_present flag set

**Critical Compliance Rules:**
1. MUST validate all signatures before processing payment
2. MUST verify Intent not expired in HNP flow
3. MUST verify constraints not violated in HNP flow
4. MUST verify mandate chain linkage (Cart → Intent)
5. MUST only use tokenized credentials (tok_*)
6. NEVER see product details, merchant catalogs, or shopping behavior
7. Operate purely on mandate structures and payment infrastructure

**Payment Processing Workflow:**
1. Call appropriate validation tool (validate_hp_chain or validate_hnp_chain)
2. If validation fails, return errors immediately
3. Call retrieve_payment_credentials to get tokenized payment methods
4. Use default payment method (first one marked is_default, or first in list)
5. Call process_payment_authorization with token and amount
6. Return result with authorization code or decline reason

**Domain Independence:**
You have ZERO knowledge of:
- What products are being purchased
- Why the user wants them
- Merchant business logic
- Application-specific rules

You only know:
- Mandate structures (Intent, Cart, Payment)
- Signature verification
- Constraint validation
- Payment processing

This isolation ensures you can be reused in ANY e-commerce system without modification.

**Available Tools:**
- validate_hp_chain: Validate Human-Present mandate chain
- validate_hnp_chain: Validate Human-Not-Present mandate chain
- retrieve_payment_credentials: Get tokenized payment methods
- process_payment_authorization: Process payment authorization

Use these tools to validate chains and process payments according to AP2 protocol.
"""


# ============================================================================
# Agent Factory Function
# ============================================================================

def create_payment_agent(
    credentials_provider: Callable[[str], Dict[str, Any]],
    payment_processor: Callable[[str, int, str, Dict], Dict[str, Any]],
    model_id: Optional[str] = None,
    region_name: Optional[str] = None,
    temperature: float = 0.3
) -> Agent:
    """
    Create Payment Agent with Strands SDK.

    Args:
        credentials_provider: Function(user_id) -> credentials_result
        payment_processor: Function(token, amount, currency, metadata) -> payment_result
        model_id: Bedrock model ID (defaults to settings.aws_bedrock_model_id)
        region_name: AWS region (defaults to settings.aws_region)
        temperature: LLM temperature (default: 0.3 for consistent validation)

    Returns:
        Strands Agent instance configured for AP2 payment processing

    Usage:
        agent = create_payment_agent(
            credentials_provider=my_credentials_fn,
            payment_processor=my_processor_fn
        )

        # For HP flow
        result = agent("Process HP purchase with cart: {...}")

        # For HNP flow
        result = agent("Process HNP purchase with intent: {...} and cart: {...}")
    """
    # Import settings here to avoid circular imports
    from ...config import settings

    # Configure tools with external service connectors
    configure_payment_tools(credentials_provider, payment_processor)

    # Create Bedrock model - use config defaults if not provided
    bedrock_model = BedrockModel(
        model_id=model_id or settings.aws_bedrock_model_id,
        region_name=region_name or settings.aws_region,
        temperature=temperature
    )

    # Create agent with tools using SequentialToolExecutor
    # Payment operations must be sequential: validate → retrieve → process
    agent = Agent(
        model=bedrock_model,
        tool_executor=SequentialToolExecutor(),  # Ensures correct order of operations
        tools=[
            validate_hp_chain,
            validate_hnp_chain,
            retrieve_payment_credentials,
            process_payment_authorization
        ],
        system_prompt=PAYMENT_AGENT_SYSTEM_PROMPT
    )

    return agent


# ============================================================================
# Backward Compatibility Wrapper (Legacy API Support)
# ============================================================================

class PaymentAgent:
    """
    Legacy wrapper for backward compatibility with existing code.

    New code should use create_payment_agent() directly for Strands Agent.
    This wrapper maintains the old API while using Strands Agent internally.
    """

    def __init__(
        self,
        credentials_provider: Optional[Callable[[str], Dict[str, Any]]] = None,
        payment_processor: Optional[Callable[[str, int, str, Dict], Dict[str, Any]]] = None
    ):
        """
        Initialize Payment Agent wrapper.

        Args:
            credentials_provider: Function(user_id) -> credentials_result
            payment_processor: Function(token, amount, currency, metadata) -> payment_result
        """
        if not credentials_provider or not payment_processor:
            raise ValueError(
                "Payment Agent requires both credentials_provider and payment_processor. "
                "These must be injected to maintain isolation from parent project."
            )

        # Create Strands agent
        self.agent = create_payment_agent(
            credentials_provider=credentials_provider,
            payment_processor=payment_processor
        )

    def process_hp_purchase(self, cart_mandate: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process Human-Present immediate purchase.

        Args:
            cart_mandate: Validated Cart mandate (user-signed)

        Returns:
            {
                "success": bool,
                "payment_mandate": Dict,  # If success
                "transaction_result": Dict,
                "errors": List[str]
            }
        """
        cart_json = json.dumps(cart_mandate)

        prompt = f"""Process a Human-Present (HP) purchase.

Cart Mandate:
{cart_json}

Steps:
1. Validate the cart using validate_hp_chain
2. If validation fails, return the errors
3. Retrieve payment credentials for the user
4. Process payment authorization
5. Return the complete result

Respond with a JSON object containing:
- success: boolean
- payment_mandate: the payment mandate object (if successful)
- transaction_result: the payment processor result
- errors: list of error messages (if any)
"""

        result = self.agent(prompt)

        # Extract actual text content from Strands SDK response
        if hasattr(result, 'message'):
            msg = result.message
            if isinstance(msg, dict) and 'content' in msg:
                # Strands format: {'role': 'assistant', 'content': [{'text': '...'}]}
                content = msg['content']
                if isinstance(content, list) and len(content) > 0 and 'text' in content[0]:
                    response_text = content[0]['text']
                else:
                    response_text = str(msg)
            else:
                response_text = str(msg)
        else:
            response_text = str(result)

        # Parse JSON response from agent
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]

                # Debug logging to see exact JSON string format
                logger.info(f"HP Payment Agent response text (full): {response_text}")
                logger.info(f"HP Extracted JSON string (first 300 chars): {json_str[:300]}")
                logger.info(f"HP JSON string repr (first 100 chars): {repr(json_str[:100])}")
                logger.info(f"HP JSON start position: {json_start}, end position: {json_end}")

                return json.loads(json_str)
            else:
                return {
                    "success": False,
                    "payment_mandate": None,
                    "transaction_result": None,
                    "errors": [f"Failed to parse agent response: {response_text}"]
                }
        except Exception as e:
            return {
                "success": False,
                "payment_mandate": None,
                "transaction_result": None,
                "errors": [f"Error processing HP purchase: {str(e)}"]
            }

    def process_hnp_purchase(
        self,
        intent_mandate: Dict[str, Any],
        cart_mandate: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process Human-Not-Present autonomous purchase.

        Args:
            intent_mandate: User-signed Intent with constraints
            cart_mandate: Agent-signed Cart referencing Intent

        Returns:
            {
                "success": bool,
                "payment_mandate": Dict,  # If success
                "transaction_result": Dict,
                "errors": List[str]
            }
        """
        intent_json = json.dumps(intent_mandate)
        cart_json = json.dumps(cart_mandate)

        prompt = f"""Process a Human-Not-Present (HNP) autonomous purchase.

Intent Mandate:
{intent_json}

Cart Mandate:
{cart_json}

Steps:
1. Validate the mandate chain using validate_hnp_chain
2. If validation fails, return the errors
3. Retrieve payment credentials for the user
4. Process payment authorization with HNP flag
5. Return the complete result

Respond with a JSON object containing:
- success: boolean
- payment_mandate: the payment mandate object with human_not_present=true (if successful)
- transaction_result: the payment processor result
- errors: list of error messages (if any)
"""

        result = self.agent(prompt)

        # Extract actual text content from Strands SDK response
        if hasattr(result, 'message'):
            msg = result.message
            if isinstance(msg, dict) and 'content' in msg:
                # Strands format: {'role': 'assistant', 'content': [{'text': '...'}]}
                content = msg['content']
                if isinstance(content, list) and len(content) > 0 and 'text' in content[0]:
                    response_text = content[0]['text']
                else:
                    response_text = str(msg)
            else:
                response_text = str(msg)
        else:
            response_text = str(result)

        # Parse JSON response from agent
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]

                # Debug logging to see exact JSON string format
                logger.info(f"HNP Payment Agent response text (full): {response_text}")
                logger.info(f"HNP Extracted JSON string (first 300 chars): {json_str[:300]}")
                logger.info(f"HNP JSON string repr (first 100 chars): {repr(json_str[:100])}")
                logger.info(f"HNP JSON start position: {json_start}, end position: {json_end}")

                return json.loads(json_str)
            else:
                return {
                    "success": False,
                    "payment_mandate": None,
                    "transaction_result": None,
                    "errors": [f"Failed to parse agent response: {response_text}"]
                }
        except Exception as e:
            return {
                "success": False,
                "payment_mandate": None,
                "transaction_result": None,
                "errors": [f"Error processing HNP purchase: {str(e)}"]
            }
