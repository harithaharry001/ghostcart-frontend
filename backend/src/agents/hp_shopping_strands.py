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


HP_SHOPPING_SYSTEM_PROMPT = """You are GhostCart's shopping specialist - help users discover products and complete immediate purchases through natural conversation.

## Your Role

You're an intelligent shopping assistant with tools to search products, create carts, request authorization, and process payments. Guide users from browsing to checkout naturally, not as a scripted bot.

## Tools Available

- `search_products(query, max_price)` - Find products by keyword
- `create_shopping_cart(product_id, quantity)` - Create cart with selected product
- `request_user_cart_signature(cart_mandate_id, cart_summary)` - Request purchase authorization
- `get_signed_cart_mandate(cart_mandate_id)` - Retrieve signed cart after approval
- `invoke_payment_processing(signed_cart_mandate)` - Process payment

## Critical System Behaviors

**Product search returns ALL matches**: The `search_products` function returns all products matching the query, NOT filtered by `max_price`. You must handle budget constraints in conversation - explain when products exceed budget and offer alternatives or ask if user wants to proceed anyway.

**Authorization requires waiting**: After calling `request_user_cart_signature()`, you must:
1. Tell the user the cart mandate ID explicitly (e.g., "Please sign cart mandate cart_hp_abc123")
2. Wait for the user's explicit confirmation before proceeding
3. The user will respond with: "I have signed the cart mandate (ID: cart_hp_...). Please proceed with payment processing."
4. Do not continue to payment until you receive this specific confirmation message

Example: "I've created cart cart_hp_abc123 for your purchase. Please approve the cart mandate (ID: cart_hp_abc123) in the signature modal that just appeared."

**Context-aware cart creation**: You have full conversation history. When a user confirms interest in a product after you've presented options (through affirmative responses, selections, or preference statements like "I prefer Apple"), proceed directly to creating the cart with that product. Don't search again - use the product_id from your previous message.

**Error handling**: If a tool call fails, explain the issue clearly and suggest next steps. Don't silently fail or retry without user input.

## Example Flow

User: "Show me coffee makers under $70"
You: `search_products("coffee maker", 70)` → Present results with prices

User: "I'll take the first one"
You: `create_shopping_cart("prod_coffee_001", 1)` → `request_user_cart_signature("cart_hp_abc", "Philips Coffee Maker - $69")` → "Great! Please approve in the modal."

User: "I have signed the cart mandate (ID: cart_hp_abc). Please proceed with payment processing."
You: `get_signed_cart_mandate("cart_hp_abc")` → `invoke_payment_processing(signed_cart)` → "Payment confirmed! Your coffee maker ships in 2 days."

## Conversation Style

Be helpful, concise, and adapt your tone to the user. Trust your judgment to create a smooth shopping experience.
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
   db_session=None,  # Database session for transaction creation
    user_id: str = "user_demo_001",  # Default user for demo
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
        user_id: User identifier for this session (defaults to user_demo_001)
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
    async def create_shopping_cart(product_id: str, quantity: int = 1) -> str:
        """
        Create shopping cart with selected product.

        Args:
            product_id: ID of product to add to cart
            quantity: Number of items (default 1)

        Returns:
            JSON string with cart mandate and SSE metadata
        """
        # Create Intent (context-only for HP) - user_id from closure
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
    def request_user_cart_signature(cart_mandate_id: str, cart_summary: str) -> str:
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
            cart_mandate_id: ID of cart mandate to sign
            cart_summary: Human-readable summary (e.g., "Philips Coffee Maker - $73.83")

        Returns:
            JSON with signature_required flag to trigger frontend modal
        """
        # user_id from closure
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
    async def invoke_payment_processing(signed_cart_mandate: str) -> str:
        """
        Invoke Payment Agent to process the payment after cart is signed.

        Payment Agent will:
        1. Validate cart signature and mandate chain
        2. Retrieve tokenized payment credentials
        3. Process payment authorization
        4. Create Payment mandate
        5. Create transaction record

        Args:
            signed_cart_mandate: JSON string of signed cart mandate

        Returns:
            JSON with payment result (authorized/declined with details)
        """
        try:
            cart_dict = json.loads(signed_cart_mandate) if isinstance(signed_cart_mandate, str) else signed_cart_mandate

            # Use the payment_agent passed from closure (it's already a Strands agent)
            # Create PaymentAgent wrapper with proper credentials/processor
            from ..agents.payment_agent.agent import PaymentAgent
            from ..mocks.credentials_provider import get_payment_methods
            from ..mocks.payment_processor import authorize_payment

            payment_agent_wrapper = PaymentAgent(
                credentials_provider=lambda uid: {"success": True, "payment_methods": get_payment_methods(uid), "error": None},
                payment_processor=authorize_payment
            )

            payment_result = payment_agent_wrapper.process_hp_purchase(cart_mandate=cart_dict)

            if not payment_result.get("success"):
                errors = payment_result.get("errors", ["Payment failed"])
                logger.error(f"❌ HP Payment failed: {errors}")
                return json.dumps({
                    "success": False,
                    "errors": errors
                })

            # Extract payment details
            transaction_result = payment_result.get("transaction_result", {})
            payment_mandate = payment_result.get("payment_mandate", {})
            cart_total = cart_dict.get("total", {})
            amount_cents = cart_total.get("grand_total_cents", 0)

            auth_code = transaction_result.get("authorization_code")
            status = "authorized" if transaction_result.get("status") == "authorized" else "declined"
            decline_reason = transaction_result.get("decline_reason")

            logger.info(f"✅ HP Payment processed! Status: {status}, Auth Code: {auth_code}, Amount: ${amount_cents/100:.2f}")

            # Create transaction record if we have db_session
            transaction_id = None
            if db_session:
                from ..services.transaction_service import create_transaction
                from ..db.models import MandateModel

                # Save payment mandate to database first
                if payment_mandate:
                    payment_db = MandateModel(
                        id=payment_mandate.get("mandate_id"),
                        mandate_type="payment",
                        user_id=user_id,
                        transaction_id=None,  # Will be updated after transaction creation
                        mandate_data=json.dumps(payment_mandate),
                        signer_identity=payment_mandate.get("signature", {}).get("signer_identity", "ap2_payment_agent"),
                        signature=json.dumps(payment_mandate.get("signature", {})),
                        signature_metadata=json.dumps({}),
                        validation_status="valid"
                    )
                    db_session.add(payment_db)
                    await db_session.commit()
                    logger.info(f"💾 Payment mandate saved: {payment_mandate.get('mandate_id')}")

                # Get intent_id from cart references if available
                cart_references = cart_dict.get("references", {})
                intent_id = cart_references.get("intent_mandate_id") if cart_references else None

                transaction = await create_transaction(
                    db=db_session,
                    user_id=user_id,
                    cart_mandate_id=cart_dict.get("mandate_id"),
                    payment_mandate_id=payment_mandate.get("mandate_id", f"payment_hp_{cart_dict.get('mandate_id', '')[-12:]}"),
                    intent_mandate_id=intent_id,
                    status=status,
                    authorization_code=auth_code,
                    decline_reason=decline_reason,
                    amount_cents=amount_cents,
                    processor_response=transaction_result
                )
                transaction_id = transaction.transaction_id
                logger.info(f"💾 HP Transaction created: {transaction_id}")
            else:
                logger.warning("No db_session provided - transaction record not created")

            return json.dumps({
                "success": True,
                "transaction_id": transaction_id,
                "authorization_code": auth_code or "N/A",
                "amount_cents": amount_cents,
                "status": status,
                "message": f"Payment authorized! Transaction ID: {transaction_id}",
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
