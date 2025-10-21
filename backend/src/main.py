"""
GhostCart Backend - FastAPI Application

AP2-compliant backend server for mandate-based payment demonstration.
Implements HP and HNP purchase flows with agent orchestration.
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import logging
import os

from .config import settings

# Set environment variables for Payment Agent (which loads directly from os.environ)
os.environ['USER_SIGNATURE_SECRET'] = settings.user_signature_secret
os.environ['AGENT_SIGNATURE_SECRET'] = settings.agent_signature_secret
os.environ['PAYMENT_AGENT_SECRET'] = settings.payment_agent_secret
from .exceptions import AP2Error
from .db.init_db import initialize_database
from .services.bedrock_service import get_bedrock_service
from .services.scheduler import start_scheduler, shutdown_scheduler
from .api.monitoring import router as monitoring_router
from .api.products import router as products_router
from .api.payments import router as payments_router
from .api.mandates import router as mandates_router
from .api.transactions import router as transactions_router
from .api.chat import router as chat_router


# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize database, connect to AWS Bedrock
    - Shutdown: Clean up resources
    """
    # Startup
    logger.info("Starting GhostCart backend server...")
    logger.info(f"Demo mode: {settings.demo_mode}")
    logger.info(f"AWS region: {settings.aws_region}")

    # Initialize database
    try:
        initialize_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize AWS Bedrock client
    try:
        get_bedrock_service()
        logger.info("Bedrock service initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock service: {e}")
        if not settings.demo_mode:
            raise
        logger.warning("Continuing without Bedrock in demo mode")

    # Start APScheduler for monitoring jobs
    try:
        start_scheduler()
        logger.info("APScheduler started for HNP monitoring jobs")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        if not settings.demo_mode:
            raise
        logger.warning("Continuing without scheduler in demo mode")

    logger.info("Server startup complete")

    yield

    # Shutdown
    logger.info("Shutting down GhostCart backend server...")

    # Stop scheduler (wait for running jobs to complete)
    try:
        shutdown_scheduler(wait=True)
        logger.info("Scheduler shutdown complete")
    except Exception as e:
        logger.error(f"Error during scheduler shutdown: {e}")


# Initialize FastAPI application
app = FastAPI(
    title="GhostCart API",
    description="AP2-compliant mandate-based payment demonstration",
    version="0.1.0",
    lifespan=lifespan,
)


# Configure CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for production deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Exception handlers for AP2 errors
@app.exception_handler(AP2Error)
async def ap2_error_handler(request: Request, exc: AP2Error):
    """
    Handle AP2 protocol errors with standardized response format.

    Returns 400 Bad Request with error details from AP2Error.to_dict().
    This ensures all AP2 errors follow the standard error response format.
    """
    logger.warning(
        f"AP2 error: {exc.error_code} - {exc.message}",
        extra={"details": exc.details}
    )

    return JSONResponse(
        status_code=400,
        content=exc.to_dict(),
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """
    Handle validation errors with user-friendly messages.

    Used for input validation failures not caught by Pydantic.
    """
    logger.warning(f"Validation error: {str(exc)}")

    return JSONResponse(
        status_code=400,
        content={
            "error_code": "validation_error",
            "message": str(exc),
            "details": {}
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )


@app.exception_handler(Exception)
async def general_error_handler(request: Request, exc: Exception):
    """
    Catch-all handler for unexpected errors.

    Logs full exception for debugging but returns generic message to client.
    """
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "error_code": "internal_error",
            "message": "An unexpected error occurred",
            "details": {"error_type": type(exc).__name__} if settings.demo_mode else {}
        },
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Credentials": "true",
        }
    )


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        Server status and version information
    """
    return {
        "status": "healthy",
        "version": "0.1.0",
        "demo_mode": settings.demo_mode,
        "environment": {
            "aws_region": settings.aws_region,
            "model": settings.aws_bedrock_model_id.split("/")[-1] if "/" in settings.aws_bedrock_model_id else settings.aws_bedrock_model_id,
        }
    }


# Include API routers
app.include_router(products_router, prefix="/api/products", tags=["Products"])
app.include_router(payments_router, prefix="/api", tags=["Payments"])
app.include_router(mandates_router, prefix="/api/mandates", tags=["Mandates"])
app.include_router(transactions_router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(monitoring_router, tags=["Monitoring"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.demo_mode,
        log_level=settings.log_level.lower()
    )
