"""
Monitoring Service

Creates and manages background monitoring jobs for HNP autonomous purchases.
Checks product conditions periodically and triggers autonomous purchase when met.

AP2 Compliance:
- Validates Intent constraints not violated during autonomous purchase
- Creates agent-signed Cart (not user-signed) when conditions met
- Sets human_not_present flag in Payment mandate
- Maintains complete audit trail: Intent → Cart → Payment → Transaction
"""
import json
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import MonitoringJobModel, MandateModel
from ..mocks.merchant_api import search_products, register_price_drop
from ..services.scheduler import scheduler, get_monitoring_interval_minutes
from ..services.mandate_service import create_intent_mandate, create_cart_mandate, get_mandate_by_id
from ..services.signature_service import sign_agent_mandate
from ..agents.payment_agent.agent import PaymentAgent
from ..exceptions import AP2Error

logger = logging.getLogger(__name__)


# ============================================================================
# Monitoring Job Creation
# ============================================================================

async def create_monitoring_job(
    db: AsyncSession,
    intent_mandate: Dict[str, Any],
    payment_agent: PaymentAgent,
    sse_manager: Any = None
) -> Dict[str, Any]:
    """
    Create and schedule a monitoring job for HNP flow.

    Args:
        db: Database session
        intent_mandate: Signed Intent mandate with constraints
        payment_agent: Payment Agent instance for autonomous purchase
        sse_manager: SSE manager for real-time notifications

    Returns:
        Job details dict

    AP2 Compliance:
    - Intent must be signed by user (pre-authorization)
    - Job stores constraints for validation during autonomous purchase
    - Job persists across server restarts via APScheduler SQLAlchemy store
    """
    intent_id = intent_mandate["mandate_id"]
    user_id = intent_mandate["user_id"]
    product_query = intent_mandate["product_query"]
    constraints = intent_mandate["constraints"]
    expiration = datetime.fromisoformat(intent_mandate["expiration"])

    # Validate Intent has user signature
    if not intent_mandate.get("signature"):
        raise AP2Error(
            "ap2:mandate:signature_invalid",
            "Intent must be signed by user for HNP monitoring"
        )

    # Note: Intent was already saved to database when agent called create_hnp_intent
    # We just need to verify it exists and has a signature

    # Get monitoring interval
    interval_minutes = get_monitoring_interval_minutes()

    # Create monitoring job record
    job_id = intent_id  # Use intent_id as job_id for easy lookup
    job_record = MonitoringJobModel(
        job_id=job_id,
        intent_mandate_id=intent_id,
        user_id=user_id,
        product_query=product_query,
        constraints=json.dumps(constraints),
        schedule_interval_minutes=interval_minutes,
        active=True,
        last_check_at=None,
        expires_at=expiration
    )

    db.add(job_record)
    await db.commit()
    await db.refresh(job_record)

    # Schedule job with APScheduler
    # Note: Don't pass db session - it will be closed by the time job runs
    # Job function will create its own session
    scheduler.add_monitoring_job(
        job_id=job_id,
        job_func=check_monitoring_conditions,
        interval_minutes=interval_minutes,
        intent_mandate_id=intent_id,
        user_id=user_id
    )

    # Register price drop for demo mode
    # Calculate target product price that results in acceptable cart total
    # Cart total = product * 1.08 + 1000 <= max_price_cents
    target_product_price = int((constraints["max_price_cents"] - 1000) / 1.08)

    register_price_drop(
        product_query=product_query,
        target_price_cents=target_product_price
    )

    logger.info(
        f"Price drop registered: {product_query} will drop to ${target_product_price/100:.2f} "
        f"(cart total will be ${constraints['max_price_cents']/100:.2f} with tax/shipping)"
    )

    logger.info(
        f"Created monitoring job: {job_id}, "
        f"interval={interval_minutes}min, "
        f"expires={expiration}"
    )

    return {
        "job_id": job_id,
        "intent_mandate_id": intent_id,
        "check_interval_minutes": interval_minutes,
        "active": True,
        "created_at": job_record.created_at.isoformat(),
        "expires_at": expiration.isoformat()
    }


# ============================================================================
# Condition Checking (APScheduler Job Function)
# ============================================================================

async def check_monitoring_conditions(
    intent_mandate_id: str,
    user_id: str
) -> None:
    """
    Check if monitoring conditions are met and trigger autonomous purchase.

    This function is called periodically by APScheduler.

    Args:
        intent_mandate_id: Intent mandate ID
        user_id: User identifier

    AP2 Compliance:
    - Verifies Intent not expired
    - Checks product availability and pricing
    - Validates delivery time against constraints
    - Triggers autonomous purchase only when ALL constraints met
    - Creates agent-signed Cart (NOT user-signed)

    Note: This function creates its own database session and PaymentAgent
    because APScheduler runs it in a separate context from the HTTP request.
    """
    from ..db.init_db import AsyncSessionLocal
    from ..agents.payment_agent.agent import create_payment_agent
    from ..mocks.credentials_provider import get_payment_methods
    from ..mocks.payment_processor import authorize_payment

    logger.info(f"🔍 Check starting: {intent_mandate_id}")

    try:
        # Create new database session for this job execution
        async with AsyncSessionLocal() as db:
            # Create Payment Agent for this execution
            def credentials_wrapper(uid: str):
                methods = get_payment_methods(uid)
                return {"success": True, "payment_methods": methods, "error": None}

            def payment_wrapper(token: str, amount: int, currency: str, metadata: dict):
                return authorize_payment(token, amount, currency, metadata)

            payment_agent = create_payment_agent(
                credentials_provider=credentials_wrapper,
                payment_processor=payment_wrapper
            )

            # No SSE for background jobs - frontend polls /api/monitoring/jobs instead
            sse_manager = None

            # Get monitoring job record
            result = await db.execute(
                select(MonitoringJobModel).where(
                    and_(
                        MonitoringJobModel.job_id == intent_mandate_id,
                        MonitoringJobModel.active == True
                    )
                )
            )
            job = result.scalar_one_or_none()

            if not job:
                logger.warning(f"Monitoring job {intent_mandate_id} not found or inactive")
                return

            # Update last check timestamp
            check_time = datetime.utcnow()
            job.last_check_at = check_time
            await db.commit()

            # Emit check starting event (FR-043)
            if sse_manager:
                await sse_manager.add_event(user_id, "monitoring_check_started", {
                    "intent_id": intent_mandate_id,
                    "timestamp": check_time.isoformat(),
                    "message": f"Checking prices at {check_time.strftime('%I:%M %p')}"
                })

            # Get Intent mandate
            intent_data = await get_mandate_by_id(db, intent_mandate_id)
            if not intent_data:
                logger.error(f"Intent mandate {intent_mandate_id} not found")
                await deactivate_job(db, intent_mandate_id, "intent_not_found")
                return

            # Check if Intent expired
            expiration = datetime.fromisoformat(intent_data["expiration"])
            if datetime.utcnow() > expiration:
                logger.info(f"Intent {intent_mandate_id} expired, deactivating job")
                await deactivate_job(db, intent_mandate_id, "expired")

                # FR-049: Include final price and option to recreate
                if sse_manager:
                    # Get current price for reference
                    products = search_products(
                        query=job.product_query,
                        max_price=None,
                        category=None
                    )
                    current_price = products[0]["price_cents"] if products else None

                    await sse_manager.add_event(user_id, "monitoring_expired", {
                        "intent_id": intent_mandate_id,
                        "product_query": job.product_query,
                        "target_price_cents": json.loads(job.constraints)["max_price_cents"],
                        "current_price_cents": current_price,
                        "message": f"Monitoring expired after 7 days without conditions being met. Current price: ${current_price/100:.2f}" if current_price else "Monitoring expired without conditions being met",
                        "action_available": "create_new_monitoring"
                    })
                return

            # Parse constraints
            constraints = json.loads(job.constraints)
            max_price_cents = constraints["max_price_cents"]
            max_delivery_days = constraints["max_delivery_days"]

            # Calculate maximum product price that would result in acceptable cart total
            # Cart total = product + tax(8%) + shipping($10)
            # Solve: product * 1.08 + 1000 <= max_price_cents
            # product <= (max_price_cents - 1000) / 1.08
            max_product_price_cents = int((max_price_cents - 1000) / 1.08)

            logger.info(
                f"Max cart total: ${max_price_cents/100:.2f}, "
                f"Max product price (before tax/shipping): ${max_product_price_cents/100:.2f}"
            )

            # Search for products matching query
            products = search_products(
                query=job.product_query,
                max_price=max_product_price_cents / 100,  # Convert cents to dollars
                category=None
            )

            logger.info(f"Found {len(products)} products for query '{job.product_query}' with max_price ${max_price_cents/100}")
            if products:
                logger.info(f"First product: {products[0]['name']} - ${products[0]['price_cents']/100:.2f}")

            # FR-048: Handle no products found with specific message
            if not products:
                logger.warning(f"No products found for query: {job.product_query}")

                if sse_manager:
                    await sse_manager.add_event(user_id, "monitoring_check_complete", {
                        "intent_id": intent_mandate_id,
                        "status": "conditions_not_met",
                        "reason": "product_not_found",
                        "message": f"No products found matching '{job.product_query}'",
                        "last_check_at": check_time.isoformat()
                    })
                return

            # Find first product meeting ALL constraints and analyze reasons
            # NOTE: max_price_cents applies to FINAL CART TOTAL (product + tax + shipping)
            matching_product = None
            best_product = products[0] if products else None  # Track best match for feedback
            reasons_not_met = []

            for product in products:
                # Calculate what the cart total would be for this product
                estimated_cart_total = int(product["price_cents"] * 1.08 + 1000)

                price_ok = estimated_cart_total <= max_price_cents
                delivery_ok = product["delivery_estimate_days"] <= max_delivery_days
                in_stock = product["stock_status"] == "in_stock"

                # Track reasons for best product
                if product == best_product:
                    if not price_ok:
                        reasons_not_met.append(f"cart total ${estimated_cart_total/100:.2f} exceeds max ${max_price_cents/100:.2f}")
                    if not delivery_ok:
                        reasons_not_met.append(f"delivery {product['delivery_estimate_days']}d exceeds max {max_delivery_days}d")
                    if not in_stock:
                        reasons_not_met.append("out of stock")

                if price_ok and delivery_ok and in_stock:
                    matching_product = product
                    break

            # FR-018 & FR-043: Emit status update when conditions not met
            if not matching_product:
                logger.debug(
                    f"No products meet constraints for {intent_mandate_id}: "
                    f"price<=${max_price_cents}¢, delivery<={max_delivery_days}d"
                )

                # Determine primary reason
                reason_text = ", ".join(reasons_not_met) if reasons_not_met else "no products meet all constraints"

                if sse_manager:
                    await sse_manager.add_event(user_id, "monitoring_check_complete", {
                        "intent_id": intent_mandate_id,
                        "status": "conditions_not_met",
                        "current_price_cents": best_product["price_cents"],
                        "current_delivery_days": best_product["delivery_estimate_days"],
                        "current_stock_status": best_product["stock_status"],
                        "target_price_cents": max_price_cents,
                        "target_delivery_days": max_delivery_days,
                        "reason": reason_text,
                        "message": f"Current price: ${best_product['price_cents']/100:.2f} - Conditions not met: {reason_text}",
                        "last_check_at": check_time.isoformat()
                    })
                return

            # Conditions met! Trigger autonomous purchase
            logger.info(
                f"Conditions met for {intent_mandate_id}! "
                f"Product: {matching_product['name']}, "
                f"Price: {matching_product['price_cents']}¢, "
                f"Delivery: {matching_product['delivery_estimate_days']}d"
            )

            # GUARD: Check if job is still active before proceeding with purchase
            # Re-fetch job to get latest state (prevents race condition with concurrent instances)
            await db.refresh(job)
            if not job.active:
                logger.warning(f"Job {intent_mandate_id} already deactivated - skipping duplicate purchase")
                return

            # GUARD: Deactivate job BEFORE purchase to prevent duplicate transactions
            # This prevents concurrent job instances from processing the same purchase
            logger.info(f"Deactivating job {intent_mandate_id} BEFORE purchase to prevent duplicates")
            await deactivate_job(db, intent_mandate_id, "purchase_starting")

            # Now trigger the purchase (job is already deactivated, so no concurrent instances will proceed)
            await trigger_autonomous_purchase(
                db=db,
                intent_data=intent_data,
                matching_product=matching_product,
                user_id=user_id,
                payment_agent=payment_agent,
                sse_manager=sse_manager
            )

            logger.info(f"✅ Check complete: {intent_mandate_id} - Purchase triggered!")

    except Exception as e:
        logger.error(f"❌ Check failed: {intent_mandate_id} - {e}", exc_info=True)
    finally:
        logger.info(f"🏁 Check finished: {intent_mandate_id}")

# ============================================================================
# Autonomous Purchase Trigger
# ============================================================================

async def trigger_autonomous_purchase(
    db: AsyncSession,
    intent_data: Dict[str, Any],
    matching_product: Dict[str, Any],
    user_id: str,
    payment_agent: PaymentAgent,
    sse_manager: Any = None
) -> Dict[str, Any]:
    """
    Trigger autonomous purchase when monitoring conditions are met.

    Args:
        db: Database session
        intent_data: Intent mandate data
        matching_product: Product that meets constraints
        user_id: User identifier
        payment_agent: Payment Agent for processing
        sse_manager: SSE manager for notifications

    Returns:
        Transaction result

    AP2 Compliance:
    - Creates Cart with AGENT signature (NOT user)
    - Cart references Intent ID (chain link)
    - Validates Cart total does not exceed Intent max_price constraint
    - Validates Cart delivery does not exceed Intent max_delivery_days constraint
    - Payment mandate has human_not_present=True flag
    - Complete audit trail: Intent (user-signed) → Cart (agent-signed) → Payment (HNP)
    """
    intent_id = intent_data["mandate_id"]
    constraints = intent_data["constraints"]

    # Emit notification: autonomous purchase starting
    if sse_manager:
        await sse_manager.add_event(user_id, "autonomous_purchase_starting", {
            "intent_id": intent_id,
            "product": {
                "name": matching_product["name"],
                "price_cents": matching_product["price_cents"],
                "delivery_days": matching_product["delivery_estimate_days"]
            },
            "message": "Conditions met! Starting autonomous purchase..."
        })

    # Build Cart items
    unit_price = matching_product["price_cents"]
    quantity = 1
    line_total = unit_price * quantity

    items = [{
        "product_id": matching_product["product_id"],
        "product_name": matching_product["name"],
        "quantity": quantity,
        "unit_price_cents": unit_price,
        "line_total_cents": line_total  # Required field
    }]

    # Calculate totals
    subtotal_cents = line_total
    tax_cents = int(subtotal_cents * 0.08)  # 8% tax
    shipping_cents = 1000  # $10 flat shipping
    grand_total_cents = subtotal_cents + tax_cents + shipping_cents

    # Validate cart total constraint (AP2 compliance: max_price applies to final cart total)
    if grand_total_cents > constraints["max_price_cents"]:
        error_msg = (
            f"Cart total {grand_total_cents}¢ (${grand_total_cents/100:.2f}) exceeds Intent constraint "
            f"{constraints['max_price_cents']}¢ (${constraints['max_price_cents']/100:.2f})"
        )
        logger.error(error_msg)

        if sse_manager:
            await sse_manager.add_event(user_id, "autonomous_purchase_failed", {
                "error": "constraints_violated",
                "message": error_msg
            })

        raise AP2Error("ap2:mandate:constraints_violated", error_msg)

    if matching_product["delivery_estimate_days"] > constraints["max_delivery_days"]:
        error_msg = (
            f"Delivery {matching_product['delivery_estimate_days']}d exceeds "
            f"Intent constraint {constraints['max_delivery_days']}d"
        )
        logger.error(error_msg)

        if sse_manager:
            await sse_manager.add_event(user_id, "autonomous_purchase_failed", {
                "error": "constraints_violated",
                "message": error_msg
            })

        raise AP2Error("ap2:mandate:constraints_violated", error_msg)

    # Create agent-signed Cart mandate
    cart_mandate = await create_cart_mandate(
        db=db,
        user_id=user_id,
        items=items,
        total={
            "subtotal_cents": subtotal_cents,
            "tax_cents": tax_cents,
            "shipping_cents": shipping_cents,
            "grand_total_cents": grand_total_cents,  # Fixed: was "total_cents"
            "currency": "USD"
        },
        merchant_info={
            "merchant_id": "merchant_ghostcart_demo",
            "merchant_name": "GhostCart Demo Store",
            "merchant_url": "https://demo.ghostcart.com"  # Required field
        },
        delivery_estimate_days=matching_product["delivery_estimate_days"],
        intent_reference=intent_id,  # Links to Intent
        signed_by="agent",  # Agent signs, NOT user
        signer_id="hnp_delegate_agent"
    )

    logger.info(
        f"Created agent-signed Cart {cart_mandate.mandate_id} "
        f"for autonomous purchase (Intent: {intent_id})"
    )

    # Emit notification: Cart created
    if sse_manager:
        await sse_manager.add_event(user_id, "autonomous_cart_created", {
            "cart_id": cart_mandate.mandate_id,
            "intent_id": intent_id,
            "total_cents": grand_total_cents,
            "agent_signed": True
        })

    # Convert Pydantic model to dict for Payment Agent
    cart_dict = json.loads(cart_mandate.model_dump_json())

    # Invoke Payment Agent with HNP flag using PaymentAgent wrapper
    logger.info(f"Invoking Payment Agent for HNP purchase validation...")

    try:
        # Use PaymentAgent wrapper (not raw agent) for proper response parsing
        from ..agents.payment_agent.agent import PaymentAgent
        from ..mocks.credentials_provider import get_payment_methods
        from ..mocks.payment_processor import authorize_payment

        payment_agent_wrapper = PaymentAgent(
            credentials_provider=lambda uid: {"success": True, "payment_methods": get_payment_methods(uid), "error": None},
            payment_processor=authorize_payment
        )

        payment_result = payment_agent_wrapper.process_hnp_purchase(
            intent_mandate=intent_data,
            cart_mandate=cart_dict
        )

        if not payment_result.get("success"):
            errors = payment_result.get("errors", ["Payment failed"])
            logger.error(f"❌ HNP Payment failed: {errors}")

            if sse_manager:
                await sse_manager.add_event(user_id, "autonomous_purchase_failed", {
                    "error": str(errors),
                    "intent_id": intent_id
                })

            return {"success": False, "errors": errors}

        # Extract payment details
        transaction_result = payment_result.get("transaction_result", {})
        payment_mandate = payment_result.get("payment_mandate", {})

        auth_code = transaction_result.get("authorization_code")
        status = "authorized" if transaction_result.get("status") == "authorized" else "declined"
        decline_reason = transaction_result.get("decline_reason")

        logger.info(f"✅ HNP Payment processed! Status: {status}, Auth Code: {auth_code}, Amount: ${grand_total_cents/100:.2f}")

        # Save payment mandate to database
        if payment_mandate:
            payment_db = MandateModel(
                id=payment_mandate.get("mandate_id"),
                mandate_type="payment",
                user_id=user_id,
                transaction_id=None,  # Will be updated after transaction creation
                mandate_data=json.dumps(payment_mandate),
                signer_identity=payment_mandate.get("signature", {}).get("signer_identity", "ap2_payment_agent"),
                signature=json.dumps(payment_mandate.get("signature", {})),
                signature_metadata=json.dumps({"human_not_present": True}),
                validation_status="valid"
            )
            db.add(payment_db)
            await db.commit()
            logger.info(f"💾 HNP Payment mandate saved: {payment_mandate.get('mandate_id')}")

        # Create transaction record
        from ..services.transaction_service import create_transaction

        transaction = await create_transaction(
            db=db,
            user_id=user_id,
            cart_mandate_id=cart_mandate.mandate_id,
            payment_mandate_id=payment_mandate.get("mandate_id", f"payment_hnp_{cart_mandate.mandate_id[-12:]}"),
            intent_mandate_id=intent_id,
            status=status,
            authorization_code=auth_code,
            decline_reason=decline_reason,
            amount_cents=grand_total_cents,
            processor_response=transaction_result
        )
        transaction_id = transaction.transaction_id
        logger.info(f"💾 HNP Transaction created: {transaction_id}")

        # Emit success notification
        if sse_manager:
            await sse_manager.add_event(user_id, "autonomous_purchase_complete", {
                "transaction_id": transaction_id,
                "authorization_code": auth_code,
                "amount_cents": grand_total_cents,
                "product_name": matching_product["name"],
                "intent_id": intent_id,
                "cart_id": cart_mandate.mandate_id,
                "message": f"Autonomous purchase completed! {matching_product['name']} for ${grand_total_cents/100:.2f}"
            })

        return {"success": True, "transaction_id": transaction_id, "authorization_code": auth_code}

    except Exception as e:
        logger.error(f"Payment Agent error during autonomous purchase: {e}", exc_info=True)

        if sse_manager:
            await sse_manager.add_event(user_id, "autonomous_purchase_failed", {
                "error": str(e),
                "intent_id": intent_id
            })

        raise


# ============================================================================
# Job Management
# ============================================================================

async def deactivate_job(
    db: AsyncSession,
    job_id: str,
    reason: str
) -> None:
    """
    Deactivate a monitoring job.

    Args:
        db: Database session
        job_id: Job identifier
        reason: Reason for deactivation (expired, purchase_complete, cancelled, etc.)
    """
    result = await db.execute(
        select(MonitoringJobModel).where(MonitoringJobModel.job_id == job_id)
    )
    job = result.scalar_one_or_none()

    if job:
        job.active = False
        await db.commit()
        logger.info(f"Deactivated monitoring job {job_id}: {reason}")

    # Remove from scheduler
    scheduler.remove_job(job_id)


async def cancel_monitoring_job(
    db: AsyncSession,
    job_id: str,
    user_id: str
) -> bool:
    """
    Cancel an active monitoring job (user-initiated).

    Args:
        db: Database session
        job_id: Job identifier
        user_id: User identifier (for authorization)

    Returns:
        True if cancelled successfully, False otherwise
    """
    result = await db.execute(
        select(MonitoringJobModel).where(
            and_(
                MonitoringJobModel.job_id == job_id,
                MonitoringJobModel.user_id == user_id,
                MonitoringJobModel.active == True
            )
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Cannot cancel job {job_id}: not found or unauthorized")
        return False

    await deactivate_job(db, job_id, "user_cancelled")
    logger.info(f"User {user_id} cancelled monitoring job {job_id}")
    return True


async def get_user_monitoring_jobs(
    db: AsyncSession,
    user_id: str,
    active_only: bool = False
) -> List[Dict[str, Any]]:
    """
    Get all monitoring jobs for a user.

    Args:
        db: Database session
        user_id: User identifier
        active_only: If True, return only active jobs

    Returns:
        List of job detail dicts
    """
    query = select(MonitoringJobModel).where(MonitoringJobModel.user_id == user_id)

    if active_only:
        query = query.where(MonitoringJobModel.active == True)

    result = await db.execute(query)
    jobs = result.scalars().all()

    job_list = []
    for job in jobs:
        # Get scheduler job info if active
        scheduler_job = scheduler.get_job(job.job_id) if job.active else None

        job_list.append({
            "job_id": job.job_id,
            "intent_mandate_id": job.intent_mandate_id,
            "product_query": job.product_query,
            "constraints": json.loads(job.constraints),
            "active": job.active,
            "schedule_interval_minutes": job.schedule_interval_minutes,
            "last_check_at": job.last_check_at.isoformat() if job.last_check_at else None,
            "created_at": job.created_at.isoformat(),
            "expires_at": job.expires_at.isoformat(),
            "next_run_time": scheduler_job.next_run_time.isoformat() if scheduler_job else None
        })

    return job_list
