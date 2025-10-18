"""
Human-Present Shopping Agent using Strands SDK

Orchestrates immediate purchase flow for AP2 protocol demonstration.
Guides user through product search → cart creation → signature → payment.

Strands SDK Integration:
Uses BedrockModel with Claude Sonnet 4.5 and custom tools for shopping flow.
"""
from typing import Dict, Any, Optional
from strands import Agent, tool
from strands.models import BedrockModel
import json
import logging

logger = logging.getLogger(__name__)

# Config will be imported inside factory function to avoid circular imports


HP_SHOPPING_SYSTEM_PROMPT = """You are the GhostCart Shopping Assistant for immediate purchases.

**Your Role:**
Help users find and purchase products right now through natural conversation using your available tools.

**Complete Purchase Workflow:**

1. **Understand Intent**
   - Ask clarifying questions about what they want to buy
   - Understand price range, preferences, urgency

2. **Search Products**
   - Use `search_products` tool with user's query and max_price
   - Present options with key details (price, stock, delivery)
   - Help user decide based on their needs
   - **After showing products, wait for user confirmation**

3. **Product Selection (Multi-Turn Conversation)**
   - When user responds with affirmative like "Yes", "I'll take it", "Add to cart", "The first one", etc.
   - **CRITICAL**: Use conversation context - you just showed them products in your previous response
   - The search_products tool returned JSON with product_id fields
   - If user says generic "Yes" or "I'll take it" → assume they want the FIRST product from your last search
   - If user specifies "the second one" or "option 2" → use that numbered product
   - If user mentions product name → match it from previous results
   - **IMMEDIATELY proceed to Build Cart - don't ask for confirmation again!**

4. **Build Cart**
   - Once user selects a product, use `create_shopping_cart` tool with the product_id
   - Provide cart summary: items, total, delivery estimate
   - Explain next step: biometric authorization

5. **Request Signature** (ASYNC - User interaction required)
   - **CRITICAL:** Use `request_user_cart_signature` tool - DO NOT ask user to type signature!
   - This tool triggers a biometric modal in the frontend UI
   - Tell user: "Please approve this purchase with your biometric authorization. A confirmation modal will appear."
   - IMPORTANT: The signature is NOT applied immediately - user must interact with frontend modal
   - The tool returns signature_required=True, which tells frontend to show the modal
   - After you call this tool, inform user that modal is ready and wait for them to complete it
   - **NEVER say things like "type your full name" or "provide signature below" - signatures are BIOMETRIC!**

   **DO NOT proceed to payment immediately after calling this tool!**
   The conversation pauses here. User will return to chat after signing in the frontend.

6. **Process Payment** (Only when user returns with signed cart)
   - After user completes signature in frontend modal, use `invoke_payment_processing` tool
   - This invokes the Payment Agent to process payment
   - Handle result:
     * **Authorized**: Celebrate! Provide transaction details
     * **Declined**: Explain reason sympathetically, offer to try different payment method

**Available Tools:**
- `search_products(query, max_price)` - Search product catalog (returns JSON with product_id, name, price_cents, etc.)
- `create_shopping_cart(user_id, product_id, quantity)` - Create cart mandate
- `request_user_cart_signature(user_id, cart_mandate_id, cart_summary)` - Request user authorization
- `get_signed_cart_mandate(cart_mandate_id)` - Retrieve signed cart from database after user signs
- `invoke_payment_processing(user_id, signed_cart_mandate)` - Process payment via Payment Agent

**Important Rules:**
1. Always search before suggesting products (don't invent items!)
2. ALWAYS use the search_products tool when user asks for products - don't describe products without searching!
3. Only recommend in-stock items from search results
4. Use tools in order: search → cart → signature → payment
5. Be transparent about what user is authorizing
6. If payment declines, empathize and offer alternatives
7. Celebrate successful purchases!
8. **When user says "Yes" after seeing products, CREATE THE CART immediately with the first product shown**
9. **You have conversation history - remember which products you showed in your last message**
10. **NEVER ask user to type their signature! ALWAYS use request_user_cart_signature tool to trigger biometric modal**
11. **DO NOT say "type your full name" or "provide signature below" - signatures are biometric via modal!**

**MULTI-TURN FLOW EXAMPLE:**

User: "I need a coffee maker under $70"
You: [Call search_products("coffee maker", 70)]
You: "I found these coffee makers under $70:
      1. Philips HD7462 - $69.00 (ships in 2 days)
      2. Keurig K-Mini - $59.99 (ships in 3 days)
      Which one would you like?"

User: "Yes!"
You: [Recognize "Yes" means first product]
You: [Call create_shopping_cart("user_demo_001", "prod_philips_hd7462", 1)]
You: "Great choice! Adding the Philips HD7462 Coffee Maker ($69) to your cart..."
You: [Call request_user_cart_signature("user_demo_001", "cart_abc123", "Philips HD7462 Coffee Maker - $73.83")]
You: "Please approve this purchase with your biometric authorization. A confirmation modal will appear on your screen."
[WAIT - User must complete biometric signature in frontend modal before proceeding]

User: "I have signed the cart mandate (ID: cart_abc123). Please proceed with payment processing."
You: [Recognize user has signed - extract cart_mandate_id from message]
You: [Call get_signed_cart_mandate("cart_abc123") to retrieve signed cart from database]
You: [Call invoke_payment_processing("user_demo_001", signed_cart_mandate_json)]
You: "Payment authorized! Your order is confirmed..."

**IMPORTANT: Retrieving Signed Cart Mandate:**
When user returns after signing, they will provide the cart mandate ID in their message:
- Look for the cart ID in messages like "I have signed the cart mandate (ID: cart_abc123)"
- Extract the mandate_id (format: "cart_hp_...")
- Use get_signed_cart_mandate tool to retrieve the signed cart from database
- Pass the retrieved signed cart JSON to invoke_payment_processing tool
- The signed cart will contain: mandate_id, user_id, items, total, signature, etc.

**AP2 Protocol Context (HP Flow):**
- You create context-only Intent (no signature needed for immediate purchase)
- User signs Cart (biometric authorization via signature tool)
- Payment Agent validates and processes (you invoke via tool)
- Transaction creates audit trail: Intent → Cart → Payment → Transaction

Keep conversation natural and friendly. Guide users through the complete purchase flow using your tools!
"""


def create_hp_shopping_agent(
    search_products_fn,
    create_intent_fn,
    create_cart_fn,
    request_signature_fn,
    payment_agent,
    product_lookup_fn=None,
    get_signed_mandate_fn=None,
    save_cart_fn=None,
    sse_emit_fn=None,
    model_id: Optional[str] = None,
    region_name: Optional[str] = None
) -> Agent:
    """
    Create HP Shopping Agent with Strands SDK.

    Context Management:
    - HP agent is STATELESS - receives context from Supervisor when called
    - Supervisor passes its full conversation history to HP agent
    - No SessionManager needed - context comes from parent agent

    Args:
        search_products_fn: Function to search product catalog
        create_intent_fn: Function to create Intent mandate
        create_cart_fn: Function to create Cart mandate
        request_signature_fn: Function to request user signature
        payment_agent: Payment Agent instance for processing
        product_lookup_fn: Optional function to lookup product by ID
        get_signed_mandate_fn: Optional function to retrieve signed cart from database
        save_cart_fn: Optional function to save unsigned cart to database
        sse_emit_fn: Optional SSE event emitter for custom events
        model_id: Bedrock model ID (defaults to settings.aws_bedrock_model_id)
        region_name: AWS region (defaults to settings.aws_region)

    Returns:
        Strands Agent configured for HP shopping flow (stateless)
    """
    
    @tool
    def search_products(query: str, max_price: Optional[float] = None) -> str:
        """
        Search product catalog for user's query.

        Args:
            query: Product search keywords (e.g., "coffee maker", "headphones")
            max_price: Optional maximum price in dollars

        Returns:
            JSON string with products for agent to describe
        """
        results = search_products_fn(query=query, max_price=max_price)

        # Emit SSE event directly so frontend can display products
        if sse_emit_fn:
            logger.info(f"Emitting product_results SSE event with {len(results[:5])} products")
            sse_emit_fn("product_results", {
                "products": results[:5],
                "query": query,
                "max_price": max_price,
                "count": len(results[:5])
            })

        # Return simple JSON for agent to use in conversation
        return json.dumps({"products": results[:5]})

    @tool
    async def create_shopping_cart(user_id: str, product_id: str, quantity: int = 1) -> str:
        """
        Create shopping cart with selected product.

        Args:
            user_id: User identifier
            product_id: ID of product to add to cart
            quantity: Number of items (default 1)

        Returns:
            JSON string with cart mandate and SSE metadata
        """
        # Create Intent (context-only for HP)
        intent = create_intent_fn(user_id, f"Purchase product {product_id}")

        # Get product details
        if not product_lookup_fn:
            return json.dumps({"error": "Product lookup not configured"})

        product = product_lookup_fn(product_id)
        if not product:
            return json.dumps({"error": "Product not found"})

        # Create Cart
        cart = create_cart_fn(user_id, intent["mandate_id"], [product], [quantity])

        # Save cart to database (unsigned - will be signed later by user)
        if save_cart_fn:
            try:
                await save_cart_fn(cart)
                logger.info(f"Saved cart {cart['mandate_id']} to database")
            except Exception as e:
                logger.error(f"Failed to save cart to database: {e}")
                return json.dumps({"error": f"Failed to save cart: {str(e)}"})

        # Emit SSE event so frontend can display cart
        if sse_emit_fn:
            logger.info(f"Emitting cart_created SSE event for cart {cart['mandate_id']}")
            # Send FULL cart mandate data (frontend needs this for signing)
            sse_emit_fn("cart_created", cart)

        # Return cart data for agent
        return json.dumps(cart)

    @tool
    def request_user_cart_signature(user_id: str, cart_mandate_id: str, cart_summary: str) -> str:
        """
        Request user to sign the cart mandate for purchase authorization.

        IMPORTANT: This triggers a biometric-style signature modal in the frontend UI.
        This tool does NOT actually sign the mandate - it sends a request to the frontend.

        Frontend Flow (per User Story 1, Scenarios 3-4):
        1. Frontend receives signature_required event via SSE
        2. Frontend displays biometric modal with fingerprint icon
        3. User sees cart summary and clicks "Confirm" button
        4. Frontend shows 1-second scanning animation
        5. Frontend calls POST /api/mandates/sign endpoint to apply signature
        6. User can then proceed with payment after signature is applied

        Args:
            user_id: User identifier
            cart_mandate_id: ID of cart mandate to sign
            cart_summary: Human-readable summary (e.g., "Philips Coffee Maker - $73.83")

        Returns:
            JSON with signature_required flag to trigger frontend modal
        """
        result = request_signature_fn(user_id, cart_mandate_id, "cart", cart_summary)

        # Emit SSE event to trigger frontend signature modal
        if sse_emit_fn:
            logger.info(f"Emitting signature_requested SSE event for cart {cart_mandate_id}")
            sse_emit_fn("signature_requested", {
                "mandate_id": cart_mandate_id,
                "mandate_type": "cart",
                "summary": cart_summary,
                "user_id": user_id
            })

        return json.dumps(result)

    @tool
    async def get_signed_cart_mandate(cart_mandate_id: str) -> str:
        """
        Retrieve a signed cart mandate from the database.

        Use this tool when user says they have signed the cart to retrieve
        the signed cart data before processing payment.

        Args:
            cart_mandate_id: The mandate_id of the cart (e.g., "cart_hp_...")

        Returns:
            JSON string of the signed cart mandate with signature
        """
        if not get_signed_mandate_fn:
            return json.dumps({
                "error": "Cart retrieval function not configured"
            })

        try:
            signed_cart = await get_signed_mandate_fn(cart_mandate_id)
            return json.dumps(signed_cart)
        except Exception as e:
            logger.error(f"Failed to retrieve signed cart {cart_mandate_id}: {e}")
            return json.dumps({
                "error": f"Failed to retrieve signed cart: {str(e)}"
            })

    @tool
    async def invoke_payment_processing(user_id: str, signed_cart_mandate: str) -> str:
        """
        Invoke Payment Agent to process the payment after cart is signed.

        Payment Agent will:
        1. Validate cart signature and mandate chain
        2. Retrieve tokenized payment credentials
        3. Process payment authorization
        4. Create Payment mandate

        Args:
            user_id: User identifier
            signed_cart_mandate: JSON string of signed cart mandate

        Returns:
            JSON with payment result (authorized/declined with details)
        """
        try:
            cart_dict = json.loads(signed_cart_mandate) if isinstance(signed_cart_mandate, str) else signed_cart_mandate

            # Invoke Payment Agent with HP flow
            # Use invoke_async for async context
            result = await payment_agent.invoke_async(f"Process human-present payment for cart {cart_dict.get('mandate_id')}. Cart mandate: {json.dumps(cart_dict)}")

            # Extract message from result
            response_text = ""
            if hasattr(result, 'message'):
                msg = result.message
                if isinstance(msg, dict) and 'content' in msg:
                    content = msg['content']
                    if isinstance(content, list) and len(content) > 0:
                        response_text = content[0].get('text', str(msg))
                    else:
                        response_text = str(content)
                else:
                    response_text = str(msg)

            return json.dumps({
                "success": True,
                "message": response_text,
                "flow": "human_present"
            })
        except Exception as e:
            logger.error(f"Payment processing failed: {e}", exc_info=True)
            return json.dumps({
                "success": False,
                "error": str(e)
            })

    # Import settings here to avoid circular imports
    from ..config import settings

    # Create Bedrock model - use config defaults if not provided
    bedrock_model = BedrockModel(
        model_id=model_id or settings.aws_bedrock_model_id,
        region_name=region_name or settings.aws_region,
        temperature=0.7
    )

    agent = Agent(
        model=bedrock_model,
        tools=[
            search_products,
            create_shopping_cart,
            request_user_cart_signature,
            get_signed_cart_mandate,
            invoke_payment_processing
        ],
        system_prompt=HP_SHOPPING_SYSTEM_PROMPT
    )

    return agent
