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

    # Store Intent in database first
    await create_intent_mandate(
        db=db,
        user_id=user_id,
        scenario="human_not_present",
        product_query=product_query,
        constraints=constraints,
        expiration=expiration,
        signature_required=True
    )

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
    scheduler.add_monitoring_job(
        job_id=job_id,
        job_func=check_monitoring_conditions,
        interval_minutes=interval_minutes,
        intent_mandate_id=intent_id,
        user_id=user_id,
        db=db,
        payment_agent=payment_agent,
        sse_manager=sse_manager
    )

    # Register price drop for demo mode (triggers after 45 seconds)
    register_price_drop(
        product_query=product_query,
        target_price_cents=constraints["max_price_cents"]
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
    user_id: str,
    db: AsyncSession,
    payment_agent: PaymentAgent,
    sse_manager: Any = None
) -> None:
    """
    Check if monitoring conditions are met and trigger autonomous purchase.

    This function is called periodically by APScheduler.

    Args:
        intent_mandate_id: Intent mandate ID
        user_id: User identifier
        db: Database session
        payment_agent: Payment Agent for autonomous purchase
        sse_manager: SSE manager for notifications

    AP2 Compliance:
    - Verifies Intent not expired
    - Checks product availability and pricing
    - Validates delivery time against constraints
    - Triggers autonomous purchase only when ALL constraints met
    - Creates agent-signed Cart (NOT user-signed)
    """
    try:
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
        job.last_check_at = datetime.utcnow()
        await db.commit()

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

            if sse_manager:
                await sse_manager.add_event(user_id, "monitoring_expired", {
                    "intent_id": intent_mandate_id,
                    "message": "Monitoring expired without conditions being met"
                })
            return

        # Parse constraints
        constraints = json.loads(job.constraints)
        max_price_cents = constraints["max_price_cents"]
        max_delivery_days = constraints["max_delivery_days"]

        # Search for products matching query
        products = search_products(
            query=job.product_query,
            max_price=max_price_cents / 100,  # Convert cents to dollars
            category=None
        )

        if not products:
            logger.debug(f"No products found for query: {job.product_query}")
            return

        # Find first product meeting ALL constraints
        matching_product = None
        for product in products:
            price_ok = product["price_cents"] <= max_price_cents
            delivery_ok = product["delivery_estimate_days"] <= max_delivery_days
            in_stock = product["stock_status"] == "in_stock"

            if price_ok and delivery_ok and in_stock:
                matching_product = product
                break

        if not matching_product:
            logger.debug(
                f"No products meet constraints for {intent_mandate_id}: "
                f"price<=${max_price_cents}¢, delivery<={max_delivery_days}d"
            )
            return

        # Conditions met! Trigger autonomous purchase
        logger.info(
            f"Conditions met for {intent_mandate_id}! "
            f"Product: {matching_product['name']}, "
            f"Price: {matching_product['price_cents']}¢, "
            f"Delivery: {matching_product['delivery_estimate_days']}d"
        )

        await trigger_autonomous_purchase(
            db=db,
            intent_data=intent_data,
            matching_product=matching_product,
            user_id=user_id,
            payment_agent=payment_agent,
            sse_manager=sse_manager
        )

        # Deactivate job after successful purchase
        await deactivate_job(db, intent_mandate_id, "purchase_complete")

    except Exception as e:
        logger.error(f"Error in monitoring check for {intent_mandate_id}: {e}", exc_info=True)


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
    items = [{
        "product_id": matching_product["product_id"],
        "product_name": matching_product["name"],
        "quantity": 1,
        "unit_price_cents": matching_product["price_cents"],
        "subtotal_cents": matching_product["price_cents"]
    }]

    # Calculate totals
    subtotal_cents = matching_product["price_cents"]
    tax_cents = int(subtotal_cents * 0.08)  # 8% tax
    shipping_cents = 1000  # $10 flat shipping
    total_cents = subtotal_cents + tax_cents + shipping_cents

    # Validate constraints BEFORE creating Cart
    if total_cents > constraints["max_price_cents"]:
        error_msg = (
            f"Cart total {total_cents}¢ exceeds Intent constraint "
            f"{constraints['max_price_cents']}¢ after tax/shipping"
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
            "total_cents": total_cents
        },
        merchant_info={
            "merchant_id": "merchant_ghostcart_demo",
            "merchant_name": "GhostCart Demo Store"
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
            "total_cents": total_cents,
            "agent_signed": True
        })

    # Convert Pydantic model to dict for Payment Agent
    cart_dict = json.loads(cart_mandate.model_dump_json())

    # Invoke Payment Agent with HNP flag
    try:
        payment_result = payment_agent.process_hnp_purchase(
            intent_mandate=intent_data,
            cart_mandate=cart_dict
        )

        if payment_result["success"]:
            logger.info(
                f"Autonomous purchase complete! "
                f"Transaction: {payment_result['transaction_result']['transaction_id']}"
            )

            # Emit success notification
            if sse_manager:
                await sse_manager.add_event(user_id, "autonomous_purchase_complete", {
                    "transaction_id": payment_result["transaction_result"]["transaction_id"],
                    "authorization_code": payment_result["transaction_result"]["authorization_code"],
                    "amount_cents": total_cents,
                    "product_name": matching_product["name"],
                    "intent_id": intent_id,
                    "cart_id": cart_mandate.mandate_id
                })

        else:
            logger.error(f"Autonomous purchase failed: {payment_result['errors']}")

            if sse_manager:
                await sse_manager.add_event(user_id, "autonomous_purchase_failed", {
                    "errors": payment_result["errors"],
                    "intent_id": intent_id
                })

        return payment_result

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
