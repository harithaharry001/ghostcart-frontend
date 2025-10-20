"""
Chat API Endpoints

Conversational interface for HP and HNP purchase flows.

AP2 Compliance:
- HP Flow: Immediate purchase with Cart signature
- HNP Flow: Monitoring setup with Intent pre-authorization
- SSE streaming for agent transparency
"""
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional, AsyncIterator
import uuid
import logging
import json

from strands import Agent

from ..db.init_db import get_db
from ..services.session_service import (
    get_session, update_session, create_session as create_session_db
)
from ..agents.payment_agent.agent import create_payment_agent
from ..agents.hp_shopping_strands import create_hp_shopping_agent
from ..agents.hnp_delegate_strands import create_hnp_delegate_agent
from ..agents.supervisor_strands import create_supervisor_agent
from ..mocks.credentials_provider import get_payment_methods
from ..mocks.payment_processor import authorize_payment
from ..mocks.merchant_api import search_products, get_product_by_id

logger = logging.getLogger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class ChatRequest(BaseModel):
    """Chat message request."""
    message: str
    session_id: Optional[str] = None
    user_id: str = "user_demo_001"  # Hardcoded for demo per Assumption 3 in spec
    conversation_state: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Chat message response."""
    session_id: str
    flow_type: str  # "hp", "hnp", "clarification", "general"
    response: str
    state: Dict[str, Any]
    actions: list[Dict[str, Any]] = []


# ============================================================================
# Helper Functions
# ============================================================================

async def create_hnp_intent_wrapper(
    user_id: str,
    product_query: str,
    max_price_cents: int,
    max_delivery_days: int,
    duration_days: int,
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Create Intent mandate for HNP flow and save to database.

    IMPORTANT: Intent must be saved to database BEFORE user signs it,
    so that /api/mandates/sign endpoint can find and update it.

    Args:
        user_id: User identifier
        product_query: Product search query
        max_price_cents: Maximum price constraint in cents
        max_delivery_days: Maximum delivery time constraint in days
        duration_days: How long to monitor for price drops
        db: Database session from endpoint

    Returns:
        Dict for JSON serialization in tools
    """
    from datetime import datetime, timedelta
    from ..services.mandate_service import create_intent_mandate

    intent_id = f"intent_hnp_{uuid.uuid4().hex[:16]}"
    expiration = datetime.utcnow() + timedelta(days=duration_days)

    constraints = {
        "max_price_cents": max_price_cents,
        "max_delivery_days": max_delivery_days,
        "currency": "USD"
    }

    # Save Intent to database
    intent_mandate = await create_intent_mandate(
        db=db,
        user_id=user_id,
        scenario="human_not_present",
        product_query=product_query,
        constraints=constraints,
        expiration=expiration,
        signature_required=True
    )

    # Convert Pydantic model to dict with ISO datetime strings
    intent_dict = intent_mandate.model_dump()

    # Ensure expiration is ISO string (Pydantic should handle this, but be explicit)
    if "expiration" in intent_dict and isinstance(intent_dict["expiration"], datetime):
        intent_dict["expiration"] = intent_dict["expiration"].isoformat()

    # Ensure signature timestamp is ISO string if present
    if "signature" in intent_dict and intent_dict["signature"]:
        if "timestamp" in intent_dict["signature"] and isinstance(intent_dict["signature"]["timestamp"], datetime):
            intent_dict["signature"]["timestamp"] = intent_dict["signature"]["timestamp"].isoformat()

    return intent_dict


def create_request_intent_signature_wrapper(sse_emit_fn):
    """Create request_intent_signature wrapper with SSE emitter"""
    def request_intent_signature_wrapper(
        user_id: str,
        mandate_id: str,
        mandate_type: str,
        summary: str,
        hnp_warning: bool = False,
        mandate_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Request user to sign Intent mandate with HNP warning"""

        # Emit SSE event to frontend to trigger signature modal
        sse_emit_fn("signature_requested", {
            "mandate_id": mandate_id,
            "mandate_type": mandate_type,
            "user_id": user_id,
            "summary": summary,
            "hnp_warning": hnp_warning,
            "mandate_data": mandate_data or {},
            "constraints": mandate_data.get("constraints") if mandate_data else None
        })

        logger.info(f"Emitted signature_requested SSE event for Intent: {mandate_id}")

        return {
            "signature_required": True,
            "mandate_id": mandate_id,
            "mandate_type": mandate_type,
            "user_id": user_id,
            "summary": summary,
            "hnp_warning": hnp_warning,
            "mandate_data": mandate_data or {},
            "message": f"Signature request sent. Please approve in the modal."
        }

    return request_intent_signature_wrapper


async def activate_monitoring_wrapper(
    user_id: str,
    intent_mandate: Dict[str, Any],
    db: AsyncSession
) -> Dict[str, Any]:
    """
    Activate monitoring job - creates actual APScheduler job.

    Async wrapper for create_monitoring_job that can be called from Strands async tools.

    Args:
        user_id: User identifier
        intent_mandate: Signed Intent mandate data
        db: Database session from endpoint

    Returns:
        Dict with job details (job_id, check_interval, expires_at)
    """
    from ..services.monitoring_service import create_monitoring_job
    from ..agents.payment_agent.agent import create_payment_agent
    from ..mocks.credentials_provider import get_payment_methods
    from ..mocks.payment_processor import authorize_payment

    # Create Payment Agent for autonomous purchases
    def credentials_wrapper(uid: str):
        methods = get_payment_methods(uid)
        return {"success": True, "payment_methods": methods, "error": None}

    def payment_wrapper(token: str, amount: int, currency: str, metadata: dict):
        return authorize_payment(token, amount, currency, metadata)

    payment_agent = create_payment_agent(
        credentials_provider=credentials_wrapper,
        payment_processor=payment_wrapper
    )

    # Use passed db session instead of creating new one
    result = await create_monitoring_job(
        db=db,
        intent_mandate=intent_mandate,
        payment_agent=payment_agent,
        sse_manager=None
    )

    logger.info(f"✅ Monitoring job activated: {result.get('job_id')}")
    return result


def credentials_provider_wrapper(user_id: str) -> Dict[str, Any]:
    """Wrapper for credentials provider."""
    try:
        methods = get_payment_methods(user_id)
        return {
            "success": True,
            "payment_methods": methods,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "payment_methods": [],
            "error": str(e)
        }


def payment_processor_wrapper(
    token: str,
    amount: int,
    currency: str,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Wrapper for payment processor."""
    result = authorize_payment(
        payment_token=token,
        amount_cents=amount,
        currency=currency,
        metadata=metadata
    )
    return result


async def get_signed_mandate_from_db(mandate_id: str, db: AsyncSession) -> Dict[str, Any]:
    """
    Retrieve a signed mandate from the database.

    Args:
        mandate_id: The mandate ID to retrieve
        db: Database session

    Returns:
        Dict with the signed mandate data
    """
    from sqlalchemy import select
    from ..db.models import MandateModel

    result = await db.execute(
        select(MandateModel).where(MandateModel.id == mandate_id)
    )
    mandate_row = result.scalar_one_or_none()

    if not mandate_row:
        raise ValueError(f"Mandate {mandate_id} not found")

    # Parse the stored mandate_data JSON
    mandate_data = json.loads(mandate_row.mandate_data)
    return mandate_data


def create_payment_agent_with_mocks() -> Agent:
    """
    Create Payment Agent with mock service connectors.

    Injects credentials provider and payment processor as dependencies
    to maintain Payment Agent isolation.
    """
    return create_payment_agent(
        credentials_provider=credentials_provider_wrapper,
        payment_processor=payment_processor_wrapper
    )


def create_intent_mandate(user_id: str, product_query: str) -> Dict[str, Any]:
    """Create Intent mandate for HP flow (context-only, no signature)."""
    import uuid
    intent_id = f"intent_hp_{uuid.uuid4().hex[:16]}"
    return {
        "mandate_id": intent_id,
        "mandate_type": "intent",
        "user_id": user_id,
        "scenario": "human_present",
        "product_query": product_query,
        "constraints": None,
        "expiration": None,
        "signature": None,
    }


def create_cart_mandate(
    user_id: str,
    intent_id: str,
    products: list,
    quantities: list
) -> Dict[str, Any]:
    """Create Cart mandate with line items."""
    import uuid
    cart_id = f"cart_hp_{uuid.uuid4().hex[:16]}"

    items = []
    subtotal_cents = 0

    for product, quantity in zip(products, quantities):
        unit_price_cents = product["price_cents"]
        line_total_cents = unit_price_cents * quantity

        items.append({
            "product_id": product["product_id"],
            "product_name": product["name"],
            "quantity": quantity,
            "unit_price_cents": unit_price_cents,
            "line_total_cents": line_total_cents  # Match LineItem model field name
        })

        subtotal_cents += line_total_cents

    tax_cents = int(subtotal_cents * 0.08)
    shipping_cents = 1000
    grand_total_cents = subtotal_cents + tax_cents + shipping_cents

    delivery_estimate_days = max(p["delivery_estimate_days"] for p in products)

    return {
        "mandate_id": cart_id,
        "mandate_type": "cart",
        "items": items,
        "total": {
            "subtotal_cents": subtotal_cents,
            "tax_cents": tax_cents,
            "shipping_cents": shipping_cents,
            "grand_total_cents": grand_total_cents,  # Match TotalObject model field name
            "currency": "USD"
        },
        "merchant_info": {
            "merchant_id": "merchant_ghostcart_demo",
            "merchant_name": "GhostCart Demo Store",
            "merchant_url": "https://demo.ghostcart.com"  # Required by MerchantInfo model
        },
        "delivery_estimate_days": delivery_estimate_days,
        "references": {
            "intent_mandate_id": intent_id  # Match ReferencesObject model structure
        },
        "signature": None
    }


async def save_cart_mandate(cart_data: Dict[str, Any], db: AsyncSession, user_id: str = None) -> None:
    """Save unsigned cart mandate to database.

    Args:
        cart_data: Cart mandate JSON (user_id not included per AP2 spec)
        db: Database session
        user_id: User ID for database record (passed separately)
    """
    from ..db.models import MandateModel

    # Get user_id from parameter, signature, or default to pending
    db_user_id = user_id
    if not db_user_id and cart_data.get("signature"):
        db_user_id = cart_data["signature"].get("signer_identity", "unknown")
    if not db_user_id:
        db_user_id = "pending"

    db_mandate = MandateModel(
        id=cart_data["mandate_id"],
        mandate_type="cart",
        user_id=db_user_id,
        transaction_id=None,
        mandate_data=json.dumps(cart_data),
        signer_identity="pending",  # Placeholder for NOT NULL constraint
        signature="pending",  # Placeholder for NOT NULL constraint
        signature_metadata=json.dumps({"status": "pending"}),  # Placeholder for NOT NULL constraint
        validation_status="unsigned",
    )

    db.add(db_mandate)
    await db.commit()
    await db.refresh(db_mandate)

    logger.info(f"Saved unsigned cart mandate to database: {cart_data['mandate_id']}")


def request_user_signature_wrapper(user_id: str, cart_mandate_id: str, mandate_type: str, cart_summary: str) -> Dict[str, Any]:
    """
    Request user signature (triggers frontend modal, does NOT auto-sign).

    Per User Story 1, Scenarios 3-4:
    - This triggers biometric-style modal in frontend
    - User sees cart summary and clicks "Confirm" button
    - Frontend shows 1-second scanning animation
    - Frontend calls POST /api/mandates/sign to apply signature
    - Then payment processing continues

    Args:
        user_id: User identifier
        cart_mandate_id: ID of cart mandate to be signed
        mandate_type: Type of mandate ("cart" for HP flow, "intent" for HNP)
        cart_summary: Human-readable summary for modal display

    Returns:
        Dict with signature_required=True to trigger frontend modal
    """
    return {
        "signature_required": True,
        "mandate_id": cart_mandate_id,
        "mandate_type": mandate_type,
        "user_id": user_id,
        "summary": cart_summary,
        "message": f"Please approve {cart_summary} with biometric authorization"
    }


# ============================================================================
# Streaming Chat Endpoint (Unified SSE + Chat)
# ============================================================================

def format_sse_event(event_type: str, data: Dict[str, Any], event_id: Optional[str] = None) -> str:
    """
    Format event according to SSE specification.

    Args:
        event_type: Event type (e.g., "agent_chunk", "tool_use", "complete")
        data: Event data payload
        event_id: Optional unique event ID

    Returns:
        Formatted SSE message string
    """
    lines = []

    if event_type:
        lines.append(f"event: {event_type}")

    if event_id:
        lines.append(f"id: {event_id}")

    if data:
        data_json = json.dumps(data)
        lines.append(f"data: {data_json}")

    lines.append("")
    lines.append("")

    return "\n".join(lines)


@router.get("/chat/stream")
async def chat_stream_endpoint(
    request: Request,
    message: str = Query(..., description="User message"),
    session_id: Optional[str] = Query(None, description="Session ID for conversation continuity"),
    user_id: str = Query("user_demo_001", description="User identifier"),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified streaming chat endpoint using Strands SDK native streaming.

    Note: Uses GET method for EventSource compatibility (EventSource only supports GET).

    This endpoint combines chat request/response with SSE streaming into a single
    connection. It uses Strands Agent.stream_async() for real-time event streaming.

    Query Parameters:
        message: User's message
        session_id: Optional session ID for conversation continuity
        user_id: User identifier (default: user_demo_001)

    Streams SSE Events:
        - connected: Initial connection with session_id
        - agent_thinking: Agent analyzing request
        - agent_chunk: Text being generated (real-time streaming)
        - tool_use: Tool being executed
        - tool_result: Tool execution result
        - complete: Final response with full state
        - error: Error occurred

    Benefits over separate /chat + /stream:
        - Single connection (simpler frontend)
        - Native Strands streaming (less custom code)
        - Real-time text generation (better UX)
        - Automatic tool transparency (SDK emits events)

    Example Usage:
        ```javascript
        const eventSource = new EventSource(
            `/api/chat/stream?message=${msg}&session_id=${sessionId}`
        );

        eventSource.addEventListener('agent_chunk', (e) => {
            const data = JSON.parse(e.data);
            appendToChat(data.text);  // Stream text as it arrives
        });

        eventSource.addEventListener('complete', (e) => {
            const data = JSON.parse(e.data);
            saveSession(data.session_id, data.state);
            eventSource.close();
        });
        ```

    Architecture:
        User Message → /api/chat/stream (SSE)
                    ↓
        Supervisor.stream_async() yields events:
            → agent_chunk (text generation)
            → tool_use (shopping_assistant called)
            → tool_result (HP agent response)
            → complete (final state)
    """

    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events from Strands agent streaming."""

        try:
            # ====================================================================
            # Session Management: Load or create session
            # ====================================================================

            if session_id:
                current_session_id = session_id
                session_data = await get_session(db, session_id)

                if not session_data:
                    logger.warning(f"Session {session_id} not found, creating new one")
                    session_data = await create_session_db(
                        db=db,
                        user_id=user_id,
                        initial_flow_type="none"
                    )
                    current_session_id = session_data["session_id"]

                state = session_data.get("context_data", {})
            else:
                # Create new session
                session_data = await create_session_db(
                    db=db,
                    user_id=user_id,
                    initial_flow_type="none"
                )
                current_session_id = session_data["session_id"]
                state = session_data.get("context_data", {})

            # Ensure required keys
            if "history" not in state:
                state["history"] = []

            # Send connection event
            yield format_sse_event("connected", {
                "session_id": current_session_id,
                "message": "Connected to chat stream"
            })

            logger.info(
                f"Chat stream: session={current_session_id}, user={user_id}, "
                f"message='{message[:50]}...', history_len={len(state.get('history', []))}"
            )

            # ====================================================================
            # Create Strands SessionManager (Option A - Supervisor Only)
            # ====================================================================

            from ..services.session_manager_factory import create_session_manager

            # Create SessionManager for this session
            # ONLY Supervisor will have SessionManager - specialist agents are stateless
            session_mgr = create_session_manager(current_session_id)
            logger.info(f"Created SessionManager for session: {current_session_id}")

            # ====================================================================
            # Create Agents
            # ====================================================================

            # Create Payment Agent
            payment_agent = create_payment_agent_with_mocks()

            # Create event queue for tool-level custom events
            # (product_results, cart_created, signature_requested, etc.)
            import asyncio
            event_queue = asyncio.Queue()

            # Create SSE emitter for tools
            def sync_sse_emit(event_type: str, data: Dict[str, Any]):
                """SSE emit for tool-level custom events (sync wrapper for async queue)"""
                try:
                    # Use put_nowait for synchronous context (tools call this synchronously)
                    event_queue.put_nowait((event_type, data))
                    logger.info(f"Queued custom SSE event: {event_type}")
                except Exception as e:
                    logger.error(f"Failed to queue SSE event {event_type}: {e}")

            # Create wrapper that passes db session to retrieval function
            async def get_mandate_wrapper(mandate_id: str):
                return await get_signed_mandate_from_db(mandate_id, db)

            # Create wrapper for saving cart mandate
            async def save_cart_wrapper(cart_data: Dict[str, Any]):
                return await save_cart_mandate(cart_data, db, user_id)

            # Create wrappers for HNP functions that pass db session
            async def create_intent_wrapper(
                user_id: str,
                product_query: str,
                max_price_cents: int,
                max_delivery_days: int = 7,
                duration_days: int = 7
            ):
                return await create_hnp_intent_wrapper(
                    user_id=user_id,
                    product_query=product_query,
                    max_price_cents=max_price_cents,
                    max_delivery_days=max_delivery_days,
                    duration_days=duration_days,
                    db=db
                )

            async def activate_monitoring_wrapper_closure(
                user_id: str,
                intent_mandate: Dict[str, Any]
            ):
                return await activate_monitoring_wrapper(
                    user_id=user_id,
                    intent_mandate=intent_mandate,
                    db=db
                )

            # Create HP Shopping Agent (STATELESS - no session_manager)
            # HP agent receives context from Supervisor's message history
            hp_agent = create_hp_shopping_agent(
                search_products_fn=search_products,
                create_intent_fn=create_intent_mandate,
                create_cart_fn=create_cart_mandate,
                request_signature_fn=request_user_signature_wrapper,
                payment_agent=payment_agent,
                product_lookup_fn=get_product_by_id,
                get_signed_mandate_fn=get_mandate_wrapper,
                save_cart_fn=save_cart_wrapper,
                sse_emit_fn=sync_sse_emit,
                db_session=db,  # Pass db session for transaction creation
                user_id=user_id  # Pass user_id so agent doesn't ask for it
            )

            # Create HNP Delegate Agent (STATELESS - no session_manager)
            # HNP agent receives context from Supervisor's message history
            hnp_agent = create_hnp_delegate_agent(
                search_products_func=search_products,
                create_intent_func=create_intent_wrapper,
                request_signature_func=create_request_intent_signature_wrapper(sync_sse_emit),
                activate_monitoring_func=activate_monitoring_wrapper_closure,
                get_signed_mandate_fn=get_mandate_wrapper,
                sse_emit_fn=sync_sse_emit,
                user_id=user_id  # Pass user_id so tools don't need to ask for it
            )

            # Create Supervisor Agent with SessionManager (ONLY agent with persistence)
            # Supervisor manages conversation state and passes context to specialist agents
            supervisor = create_supervisor_agent(
                hp_shopping_agent=hp_agent,
                hnp_delegate_agent=hnp_agent,
                session_manager=session_mgr,  # ONLY Supervisor has SessionManager
                event_queue=event_queue
            )

            # ====================================================================
            # Stream Agent Execution
            # ====================================================================

            # No manual context passing needed!
            # Supervisor's SessionManager automatically loads conversation history
            # Supervisor passes its full context to specialist agents when calling them

            # Emit thinking event
            yield format_sse_event("agent_thinking", {
                "message": "Understanding your request..."
            })

            response_text = ""
            final_result = None

            # Stream events from Supervisor
            # Just pass current message - SessionManager handles history automatically!
            async for event in supervisor.stream_async(message):

                # Check if client disconnected
                if await request.is_disconnected():
                    logger.info(f"Client disconnected from session: {current_session_id}")
                    break

                # Check for custom tool events in queue and yield them
                # Process all queued events before handling next Strands event
                while not event_queue.empty():
                    try:
                        custom_event_type, custom_event_data = event_queue.get_nowait()
                        logger.info(f"Yielding custom SSE event: {custom_event_type}")
                        yield format_sse_event(custom_event_type, custom_event_data)
                    except asyncio.QueueEmpty:
                        break

                # Handle different event types from Strands SDK

                # Text chunk being generated
                if "data" in event:
                    text_chunk = event["data"]
                    response_text += text_chunk
                    yield format_sse_event("agent_chunk", {
                        "text": text_chunk,
                        "complete": False
                    })

                # Tool being executed
                if "current_tool_use" in event:
                    tool_info = event["current_tool_use"]
                    tool_name = tool_info.get("name")

                    # Emit routing event when Supervisor delegates to specialist agents
                    if tool_name in ["shopping_assistant", "monitoring_assistant"]:
                        yield format_sse_event("tool_use", {
                            "tool_name": tool_name,
                            "tool_input": tool_info.get("input"),
                            "message": "Routing to specialized agent..."
                        })
                    else:
                        yield format_sse_event("tool_use", {
                            "tool_name": tool_name,
                            "tool_input": tool_info.get("input"),
                            "message": f"Executing {tool_name}..."
                        })

                # Final result
                if "result" in event:
                    final_result = event["result"]

            # ====================================================================
            # Extract Final Response
            # ====================================================================

            if final_result:
                if hasattr(final_result, 'message'):
                    msg = final_result.message
                    if isinstance(msg, dict) and 'content' in msg:
                        content = msg['content']
                        if isinstance(content, list) and len(content) > 0:
                            response_text = content[0].get('text', str(msg))
                        else:
                            response_text = str(content)
                    else:
                        response_text = str(msg)
                elif hasattr(final_result, 'content'):
                    content = final_result.content
                    if isinstance(content, list) and len(content) > 0:
                        response_text = content[0].get('text', str(content))
                    else:
                        response_text = str(content)

            logger.info(f"Supervisor stream complete: {response_text[:100]}...")

            # ====================================================================
            # Session State Update (Automatic via SessionManager)
            # ====================================================================

            # No manual session update needed!
            # Supervisor's SessionManager automatically saves conversation history
            # The Strands SDK persists the updated messages to session storage

            # We still keep the database session record for tracking purposes
            state["history"].append({
                "role": "user",
                "content": message
            })
            state["history"].append({
                "role": "assistant",
                "content": response_text
            })

            await update_session(
                db=db,
                session_id=current_session_id,
                context_data=state
            )

            # ====================================================================
            # Send Completion Event
            # ====================================================================

            yield format_sse_event("complete", {
                "session_id": current_session_id,
                "response": response_text,
                "flow_type": "supervisor"
            })

        except Exception as e:
            logger.error(f"Chat stream error: {e}", exc_info=True)
            yield format_sse_event("error", {
                "message": f"Error: {str(e)}",
                "error_type": type(e).__name__
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
