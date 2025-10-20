"""
APScheduler Configuration for Monitoring Jobs

Configures persistent background job scheduler for HNP autonomous monitoring.
Jobs survive server restarts via SQLAlchemyJobStore.

AP2 Compliance:
- Periodic checks for product availability and pricing
- Autonomous purchase triggers when constraints met
- Job persistence across restarts (SC-009: 100% survival rate)
"""
import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.asyncio import AsyncIOExecutor

from ..config import settings

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    """
    Singleton scheduler for monitoring jobs with persistent storage.

    Uses APScheduler with SQLAlchemy job store to ensure jobs survive server restarts.
    """

    _instance: Optional["MonitoringScheduler"] = None
    _scheduler: Optional[AsyncIOScheduler] = None

    def __new__(cls):
        """Singleton pattern to ensure only one scheduler instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize scheduler if not already initialized."""
        if self._scheduler is None:
            self._initialize_scheduler()

    def _initialize_scheduler(self):
        """
        Configure APScheduler with SQLAlchemy job store.

        Configuration:
        - AsyncIOScheduler for async job execution
        - SQLAlchemyJobStore backed by SEPARATE SQLite database (prevents locking conflicts)
        - AsyncIOExecutor for concurrent job execution
        - Coalesce: True (skip missed runs on restart)
        - Max instances: 3 per job (prevent overlap)
        - WAL mode enabled for better concurrency
        """
        # Use separate database for APScheduler to prevent locking conflicts
        scheduler_db_path = settings.database_path.replace('.db', '_scheduler.db')
        
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=f'sqlite:///{scheduler_db_path}',
                tablename='apscheduler_jobs',
                engine_options={
                    'connect_args': {
                        'timeout': 30,  # Increase timeout to 30 seconds
                        'check_same_thread': False
                    },
                    'pool_pre_ping': True,
                    'pool_recycle': 3600
                }
            )
        }

        executors = {
            'default': AsyncIOExecutor()
        }

        job_defaults = {
            'coalesce': True,  # Combine missed runs into one
            'max_instances': 3,  # Max concurrent instances per job
            'misfire_grace_time': 300  # 5 minutes grace period for misfires
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

        logger.info("APScheduler initialized with SQLAlchemy job store")

    def start(self):
        """
        Start the scheduler.

        Resumes existing jobs from database on startup.
        Should be called during FastAPI app startup.
        """
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info(f"Scheduler started. Existing jobs: {len(self._scheduler.get_jobs())}")

            # Log existing jobs
            for job in self._scheduler.get_jobs():
                logger.info(f"  - Job {job.id}: next_run={job.next_run_time}")
        else:
            logger.warning("Scheduler already running")

    def shutdown(self, wait: bool = True):
        """
        Shutdown the scheduler gracefully.

        Args:
            wait: Wait for running jobs to complete before shutdown

        Should be called during FastAPI app shutdown.
        """
        if self._scheduler and self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info(f"Scheduler shutdown (wait={wait})")

    def add_monitoring_job(
        self,
        job_id: str,
        job_func,
        interval_minutes: int,
        **kwargs
    ) -> str:
        """
        Add a new monitoring job to the scheduler.

        Args:
            job_id: Unique job identifier (intent_mandate_id)
            job_func: Async function to execute periodically
            interval_minutes: How often to run job
            **kwargs: Additional arguments to pass to job_func

        Returns:
            Job ID

        Example:
            scheduler.add_monitoring_job(
                job_id="intent_hnp_abc123",
                job_func=check_monitoring_conditions,
                interval_minutes=5,
                intent_mandate_id="intent_hnp_abc123",
                user_id="user_123"
            )
        """
        trigger = IntervalTrigger(minutes=interval_minutes)

        self._scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            name=f"Monitor: {job_id}",
            replace_existing=True,  # Replace if job with same ID exists
            kwargs=kwargs
        )

        next_run = self._scheduler.get_job(job_id).next_run_time
        logger.info(f"Added monitoring job: {job_id}, interval={interval_minutes}min, next_run={next_run}")

        return job_id

    def remove_job(self, job_id: str) -> bool:
        """
        Remove a monitoring job from the scheduler.

        Args:
            job_id: Job identifier to remove

        Returns:
            True if job was found and removed, False otherwise
        """
        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"Removed monitoring job: {job_id}")
            return True
        except Exception as e:
            logger.warning(f"Failed to remove job {job_id}: {e}")
            return False

    def get_job(self, job_id: str):
        """
        Retrieve job details by ID.

        Args:
            job_id: Job identifier

        Returns:
            APScheduler Job object or None if not found
        """
        return self._scheduler.get_job(job_id)

    def get_all_jobs(self):
        """
        Get all scheduled jobs.

        Returns:
            List of APScheduler Job objects
        """
        return self._scheduler.get_jobs()

    def pause_job(self, job_id: str):
        """
        Pause a monitoring job temporarily.

        Args:
            job_id: Job identifier to pause
        """
        self._scheduler.pause_job(job_id)
        logger.info(f"Paused monitoring job: {job_id}")

    def resume_job(self, job_id: str):
        """
        Resume a paused monitoring job.

        Args:
            job_id: Job identifier to resume
        """
        self._scheduler.resume_job(job_id)
        logger.info(f"Resumed monitoring job: {job_id}")


# ============================================================================
# Global Scheduler Instance
# ============================================================================

# Singleton instance - import this in other modules
scheduler = MonitoringScheduler()


# ============================================================================
# Demo Mode Support
# ============================================================================

def get_monitoring_interval_minutes() -> int:
    """
    Get monitoring interval based on demo mode setting.

    Returns:
        10 seconds (0.167 minutes) if demo_mode=True, otherwise 5 minutes

    AP2 Compliance Note:
    Demo mode accelerates monitoring for hackathon demonstration purposes.
    Production systems should use longer intervals (5+ minutes).
    """
    if settings.demo_mode:
        # Demo mode: Check every 10 seconds for faster demo
        # Matches price drop delay so purchase happens immediately after price drops
        return 0.167  # 10 seconds = 0.167 minutes (APScheduler accepts fractional minutes)
    else:
        # Production mode: Check every 5 minutes
        return 5


# ============================================================================
# Scheduler Lifecycle Functions (for FastAPI integration)
# ============================================================================

def _restore_price_drops():
    """
    Re-register price drops for active monitoring jobs after server restart.

    Since _price_drops dictionary is in-memory, it's lost on restart.
    This function reads active jobs from database and re-registers their price drops.
    """
    from datetime import datetime, timedelta
    from ..mocks.merchant_api import register_price_drop
    from ..mocks import merchant_api
    import sqlite3
    import json

    try:
        # Use direct SQLite connection (simpler for startup, avoids async issues)
        conn = sqlite3.connect(settings.database_path)
        cursor = conn.cursor()

        # Get all active jobs
        cursor.execute(
            "SELECT job_id, product_query, constraints FROM monitoring_jobs WHERE active = 1"
        )
        active_jobs = cursor.fetchall()

        for job_id, product_query, constraints_json in active_jobs:
            # Parse constraints to get target price
            constraints = json.loads(constraints_json)
            target_price_cents = constraints.get("max_price_cents")

            if target_price_cents:
                # Register the price drop
                register_price_drop(product_query, target_price_cents)

                # Backdate activation time so price drop is already active
                # (jobs may have been running for a while before restart)
                query_lower = product_query.lower()
                if query_lower in merchant_api._price_drops:
                    merchant_api._price_drops[query_lower]['activated_at'] = datetime.utcnow() - timedelta(seconds=60)

                logger.info(
                    f"Restored price drop for job {job_id}: "
                    f"{product_query} -> ${target_price_cents/100:.2f}"
                )

        conn.close()
    except Exception as e:
        logger.error(f"Failed to restore price drops: {e}", exc_info=True)


def start_scheduler():
    """
    Start the scheduler during app startup.

    Should be called in FastAPI lifespan/startup event.
    Also re-registers price drops for active monitoring jobs.
    """
    scheduler.start()

    # Re-register price drops for active jobs (since _price_drops is in-memory)
    _restore_price_drops()


def shutdown_scheduler(wait: bool = True):
    """
    Shutdown the scheduler during app shutdown.

    Args:
        wait: Wait for running jobs to complete

    Should be called in FastAPI lifespan/shutdown event.
    """
    scheduler.shutdown(wait=wait)
