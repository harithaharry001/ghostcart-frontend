"""
Session Management Service

Handles user session persistence for conversation continuity across
multi-turn interactions.

AP2 Compliance:
- Stores conversation history for Supervisor context
- Tracks current flow type (HP, HNP, clarification)
- Maintains session state across requests
- Supports multi-turn clarification conversations
"""
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from ..db.models import SessionModel

logger = logging.getLogger(__name__)


# ============================================================================
# Session Creation
# ============================================================================

async def create_session(
    db: AsyncSession,
    user_id: str,
    initial_flow_type: Optional[str] = None,
    initial_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new user session.

    Args:
        db: Database session
        user_id: User identifier
        initial_flow_type: Optional initial flow type ("hp", "hnp", "none")
        initial_context: Optional initial context data

    Returns:
        Created session data:
        {
            "session_id": str,
            "user_id": str,
            "current_flow_type": str,
            "context_data": Dict,
            "created_at": str,
            "last_activity_at": str
        }
    """
    session_id = f"session_{uuid.uuid4().hex[:16]}"

    context_data = initial_context or {
        "history": [],
        "intent": None,
        "cart": None,
        "products": [],
        "stage": "initial"
    }

    now = datetime.utcnow()

    db_session = SessionModel(
        session_id=session_id,
        user_id=user_id,
        current_flow_type=initial_flow_type or "none",
        context_data=json.dumps(context_data),
        last_activity_at=now,
        created_at=now
    )

    db.add(db_session)
    await db.commit()
    await db.refresh(db_session)

    logger.info(f"Created session: {session_id} for user {user_id}")

    return {
        "session_id": session_id,
        "user_id": user_id,
        "current_flow_type": initial_flow_type or "none",
        "context_data": context_data,
        "created_at": now.isoformat(),
        "last_activity_at": now.isoformat()
    }


# ============================================================================
# Session Retrieval
# ============================================================================

async def get_session(
    db: AsyncSession,
    session_id: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve session by ID.

    Args:
        db: Database session
        session_id: Session identifier

    Returns:
        Session data dict or None if not found:
        {
            "session_id": str,
            "user_id": str,
            "current_flow_type": str,
            "context_data": Dict,
            "created_at": str,
            "last_activity_at": str
        }
    """
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        return None

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "current_flow_type": session.current_flow_type,
        "context_data": json.loads(session.context_data) if session.context_data else {},
        "created_at": session.created_at.isoformat(),
        "last_activity_at": session.last_activity_at.isoformat()
    }


async def get_user_sessions(
    db: AsyncSession,
    user_id: str,
    active_only: bool = False,
    limit: int = 10
) -> list[Dict[str, Any]]:
    """
    Retrieve all sessions for a user.

    Args:
        db: Database session
        user_id: User identifier
        active_only: If True, only return sessions with recent activity
        limit: Maximum number of sessions to return

    Returns:
        List of session data dicts, ordered by last_activity_at descending
    """
    query = select(SessionModel).where(SessionModel.user_id == user_id)

    if active_only:
        # Filter for sessions active in last 24 hours
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(hours=24)
        query = query.where(SessionModel.last_activity_at >= cutoff)

    query = query.order_by(SessionModel.last_activity_at.desc()).limit(limit)

    result = await db.execute(query)
    sessions = result.scalars().all()

    return [
        {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "current_flow_type": session.current_flow_type,
            "context_data": json.loads(session.context_data) if session.context_data else {},
            "created_at": session.created_at.isoformat(),
            "last_activity_at": session.last_activity_at.isoformat()
        }
        for session in sessions
    ]


# ============================================================================
# Session Updates
# ============================================================================

async def update_session(
    db: AsyncSession,
    session_id: str,
    flow_type: Optional[str] = None,
    context_data: Optional[Dict[str, Any]] = None,
    append_to_history: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Update session state and context.

    Args:
        db: Database session
        session_id: Session identifier
        flow_type: Optional new flow type to set
        context_data: Optional complete context data to replace
        append_to_history: Optional message to append to history
            {"role": "user"|"assistant", "content": str}

    Returns:
        Updated session data dict or None if not found

    AP2 Compliance:
    Multi-turn conversation support for Supervisor clarifications.
    Updates last_activity_at to maintain session freshness.
    """
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        logger.warning(f"Session not found for update: {session_id}")
        return None

    # Update flow type if provided
    if flow_type is not None:
        session.current_flow_type = flow_type

    # Update context data
    if context_data is not None:
        session.context_data = json.dumps(context_data)
    elif append_to_history is not None:
        # Append to history in existing context
        current_context = json.loads(session.context_data) if session.context_data else {}
        history = current_context.get("history", [])
        history.append(append_to_history)
        current_context["history"] = history
        session.context_data = json.dumps(current_context)

    # Update activity timestamp
    session.last_activity_at = datetime.utcnow()

    await db.commit()
    await db.refresh(session)

    logger.info(f"Updated session: {session_id}, flow={flow_type}")

    return {
        "session_id": session.session_id,
        "user_id": session.user_id,
        "current_flow_type": session.current_flow_type,
        "context_data": json.loads(session.context_data) if session.context_data else {},
        "created_at": session.created_at.isoformat(),
        "last_activity_at": session.last_activity_at.isoformat()
    }


# ============================================================================
# Conversation History Management
# ============================================================================

async def get_conversation_history(
    db: AsyncSession,
    session_id: str,
    limit: Optional[int] = None
) -> list[Dict[str, str]]:
    """
    Get conversation history for a session.

    Args:
        db: Database session
        session_id: Session identifier
        limit: Optional maximum number of messages to return (most recent)

    Returns:
        List of conversation messages:
        [
            {"role": "user"|"assistant", "content": str},
            ...
        ]

    AP2 Compliance:
    Provides conversation context for Supervisor's linguistic analysis
    in multi-turn clarification flows.
    """
    session_data = await get_session(db, session_id)

    if not session_data:
        return []

    history = session_data.get("context_data", {}).get("history", [])

    if limit and len(history) > limit:
        # Return most recent messages
        history = history[-limit:]

    return history


async def clear_conversation_history(
    db: AsyncSession,
    session_id: str
) -> bool:
    """
    Clear conversation history for a session while keeping other context.

    Args:
        db: Database session
        session_id: Session identifier

    Returns:
        True if successful, False if session not found
    """
    result = await db.execute(
        select(SessionModel).where(SessionModel.session_id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        return False

    # Clear history but keep other context
    current_context = json.loads(session.context_data) if session.context_data else {}
    current_context["history"] = []
    session.context_data = json.dumps(current_context)
    session.last_activity_at = datetime.utcnow()

    await db.commit()

    logger.info(f"Cleared conversation history for session: {session_id}")
    return True


# ============================================================================
# Session Cleanup
# ============================================================================

async def delete_inactive_sessions(
    db: AsyncSession,
    days_inactive: int = 7
) -> int:
    """
    Delete sessions inactive for specified number of days.

    Args:
        db: Database session
        days_inactive: Number of days of inactivity before deletion

    Returns:
        Number of sessions deleted
    """
    from datetime import timedelta
    from sqlalchemy import delete

    cutoff = datetime.utcnow() - timedelta(days=days_inactive)

    result = await db.execute(
        delete(SessionModel).where(SessionModel.last_activity_at < cutoff)
    )

    deleted_count = result.rowcount
    await db.commit()

    logger.info(f"Deleted {deleted_count} inactive sessions (older than {days_inactive} days)")
    return deleted_count
