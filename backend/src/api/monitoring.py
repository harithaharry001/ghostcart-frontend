"""
Monitoring API Endpoints

Provides REST API for managing HNP autonomous monitoring jobs.

Endpoints:
- GET /api/monitoring/jobs - List user's monitoring jobs
- DELETE /api/monitoring/jobs/{job_id} - Cancel active monitoring job

AP2 Compliance:
- Users can view all their monitoring jobs with real-time status
- Users can cancel monitoring at any time
- Job history preserved for audit trail
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
import logging

from ..db import get_db
from ..services.monitoring_service import (
    get_user_monitoring_jobs,
    cancel_monitoring_job,
    check_monitoring_conditions
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ============================================================================
# List Monitoring Jobs
# ============================================================================

@router.get("/jobs")
async def list_monitoring_jobs(
    user_id: str = Query(..., description="User identifier"),
    active_only: bool = Query(False, description="Return only active jobs"),
    db: AsyncSession = Depends(get_db)
):
    """
    List all monitoring jobs for a user.

    Query Parameters:
    - user_id: User identifier (required)
    - active_only: If true, return only active jobs (default: false)

    Returns:
    ```json
    {
        "jobs": [
            {
                "job_id": "intent_hnp_abc123",
                "intent_mandate_id": "intent_hnp_abc123",
                "product_query": "Apple AirPods Pro",
                "constraints": {
                    "max_price_cents": 18000,
                    "max_delivery_days": 2,
                    "currency": "USD"
                },
                "active": true,
                "schedule_interval_minutes": 5,
                "last_check_at": "2025-10-17T20:15:00Z",
                "created_at": "2025-10-17T18:00:00Z",
                "expires_at": "2025-10-24T18:00:00Z",
                "next_run_time": "2025-10-17T20:20:00Z"
            }
        ],
        "total": 1,
        "active_count": 1
    }
    ```

    AP2 Transparency:
    Users can see complete monitoring state including:
    - What's being monitored (product_query)
    - Authorization constraints (max price, max delivery)
    - Job status (active/inactive)
    - Last check timestamp
    - Next scheduled check
    - Expiration time
    """
    try:
        jobs = await get_user_monitoring_jobs(
            db=db,
            user_id=user_id,
            active_only=active_only
        )

        active_count = sum(1 for job in jobs if job["active"])

        logger.info(
            f"Listed monitoring jobs for user {user_id}: "
            f"total={len(jobs)}, active={active_count}"
        )

        return {
            "jobs": jobs,
            "total": len(jobs),
            "active_count": active_count
        }

    except Exception as e:
        logger.error(f"Error listing monitoring jobs for {user_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list monitoring jobs: {str(e)}"
        )


# ============================================================================
# Cancel Monitoring Job
# ============================================================================

@router.delete("/jobs/{job_id}")
async def cancel_job(
    job_id: str,
    user_id: str = Query(..., description="User identifier for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """
    Cancel an active monitoring job.

    Path Parameters:
    - job_id: Job identifier (Intent mandate ID)

    Query Parameters:
    - user_id: User identifier (required for authorization)

    Returns:
    ```json
    {
        "success": true,
        "job_id": "intent_hnp_abc123",
        "message": "Monitoring job cancelled successfully"
    }
    ```

    Error Responses:
    - 404: Job not found or already inactive
    - 403: User not authorized to cancel this job
    - 500: Server error

    AP2 User Control:
    Users can revoke pre-authorization at any time by cancelling monitoring.
    Job record preserved in database for audit trail but marked inactive.
    APScheduler job removed from execution queue.
    """
    try:
        success = await cancel_monitoring_job(
            db=db,
            job_id=job_id,
            user_id=user_id
        )

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Monitoring job {job_id} not found, already inactive, or not authorized"
            )

        logger.info(f"User {user_id} cancelled monitoring job {job_id}")

        return {
            "success": True,
            "job_id": job_id,
            "message": "Monitoring job cancelled successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel monitoring job: {str(e)}"
        )


# ============================================================================
# Get Job Details (Optional - for detailed view)
# ============================================================================

@router.get("/jobs/{job_id}")
async def get_job_details(
    job_id: str,
    user_id: str = Query(..., description="User identifier for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a specific monitoring job.

    Path Parameters:
    - job_id: Job identifier

    Query Parameters:
    - user_id: User identifier (required for authorization)

    Returns:
    ```json
    {
        "job_id": "intent_hnp_abc123",
        "intent_mandate_id": "intent_hnp_abc123",
        "product_query": "Apple AirPods Pro",
        "constraints": {
            "max_price_cents": 18000,
            "max_delivery_days": 2,
            "currency": "USD"
        },
        "active": true,
        "schedule_interval_minutes": 5,
        "last_check_at": "2025-10-17T20:15:00Z",
        "created_at": "2025-10-17T18:00:00Z",
        "expires_at": "2025-10-24T18:00:00Z",
        "next_run_time": "2025-10-17T20:20:00Z",
        "checks_performed": 12,
        "status_reason": "conditions_not_met_price_too_high"
    }
    ```

    Error Responses:
    - 404: Job not found
    - 403: User not authorized to view this job
    """
    try:
        jobs = await get_user_monitoring_jobs(
            db=db,
            user_id=user_id,
            active_only=False
        )

        # Find specific job
        job = next((j for j in jobs if j["job_id"] == job_id), None)

        if not job:
            raise HTTPException(
                status_code=404,
                detail=f"Monitoring job {job_id} not found or not authorized"
            )

        return job

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job {job_id} details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get job details: {str(e)}"
        )


# ============================================================================
# Manual Check Trigger (Demo Mode)
# ============================================================================

@router.post("/jobs/{job_id}/check")
async def trigger_manual_check(
    job_id: str,
    user_id: str = Query(..., description="User identifier for authorization"),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger a monitoring check for demo purposes.

    **DEMO MODE ONLY:** Instead of waiting 30 seconds for the next scheduled check,
    this endpoint immediately checks if the product conditions are met and triggers
    autonomous purchase if they are.

    Path Parameters:
    - job_id: Job identifier (Intent mandate ID)

    Query Parameters:
    - user_id: User identifier (required for authorization)

    Returns:
    ```json
    {
        "success": true,
        "job_id": "intent_hnp_abc123",
        "message": "Check triggered - conditions met, autonomous purchase initiated!"
        // OR
        "message": "Check complete - conditions not yet met"
    }
    ```

    Use Cases:
    - Demo: Immediately test autonomous purchase flow
    - Testing: Verify monitoring logic without waiting
    - Debugging: Force condition check on demand

    Example:
    ```bash
    curl -X POST "http://localhost:8000/api/monitoring/jobs/intent_hnp_abc123/check?user_id=user_demo_001"
    ```
    """
    try:
        # Verify job exists and user is authorized
        from ..db.models import MonitoringJobModel
        from sqlalchemy import select, and_

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
            raise HTTPException(
                status_code=404,
                detail=f"Monitoring job {job_id} not found, inactive, or not authorized"
            )

        logger.info(f"Manual check triggered for job {job_id} by user {user_id}")

        # Get Payment Agent (need to create it here since we don't have it in scope)
        from ..agents.payment_agent.agent import create_payment_agent
        from ..mocks.credentials_provider import get_payment_methods
        from ..mocks.payment_processor import authorize_payment

        def credentials_wrapper(uid: str):
            methods = get_payment_methods(uid)
            return {"success": True, "payment_methods": methods, "error": None}

        def payment_wrapper(token: str, amount: int, currency: str, metadata: dict):
            return authorize_payment(token, amount, currency, metadata)

        payment_agent = create_payment_agent(
            credentials_provider=credentials_wrapper,
            payment_processor=payment_wrapper
        )

        # Trigger the check
        await check_monitoring_conditions(
            intent_mandate_id=job_id,
            user_id=user_id,
            db=db,
            payment_agent=payment_agent,
            sse_manager=None  # Could add SSE support here
        )

        # Check if job is still active (it gets deactivated after successful purchase)
        await db.refresh(job)

        if not job.active:
            message = "✅ Conditions met! Autonomous purchase initiated and completed."
            logger.info(f"Job {job_id} deactivated after manual check - purchase completed")
        else:
            message = "⏳ Conditions not yet met. Monitoring continues..."

        return {
            "success": True,
            "job_id": job_id,
            "message": message,
            "job_active": job.active,
            "last_check_at": job.last_check_at.isoformat() if job.last_check_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering manual check for {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger manual check: {str(e)}"
        )
