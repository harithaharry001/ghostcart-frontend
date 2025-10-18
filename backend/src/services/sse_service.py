"""
Server-Sent Events (SSE) Service

Manages real-time event streaming to frontend clients for agent transparency.
Provides session-based event queues for HP and HNP flows.

AP2 Compliance: Enables real-time monitoring of agent decision-making
and mandate generation for transparency and auditability.
"""
import asyncio
from typing import Dict, Any, Optional, AsyncIterator
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class SSEManager:
    """
    Server-Sent Events manager with session-based event queues.

    Manages event queues per session ID, allowing multiple concurrent
    flows to stream events independently.
    """

    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize SSE manager.

        Args:
            session_timeout_minutes: Inactive session cleanup threshold
        """
        # Session queues: {session_id: asyncio.Queue}
        self._queues: Dict[str, asyncio.Queue] = {}

        # Session metadata: {session_id: {"created_at": datetime, "last_activity": datetime}}
        self._sessions: Dict[str, Dict[str, datetime]] = {}

        # Session timeout for cleanup
        self._session_timeout = timedelta(minutes=session_timeout_minutes)

        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

        logger.info(f"SSE Manager initialized (session timeout: {session_timeout_minutes}m)")

    async def create_session(self, session_id: str) -> None:
        """
        Create a new session with event queue.

        Args:
            session_id: Unique session identifier
        """
        async with self._lock:
            if session_id not in self._queues:
                self._queues[session_id] = asyncio.Queue()
                self._sessions[session_id] = {
                    "created_at": datetime.utcnow(),
                    "last_activity": datetime.utcnow(),
                }
                logger.info(f"Created SSE session: {session_id}")

    async def add_event(
        self,
        session_id: str,
        event_type: str,
        data: Dict[str, Any],
        event_id: Optional[str] = None
    ) -> None:
        """
        Add event to session queue.

        Args:
            session_id: Target session identifier
            event_type: Event type (e.g., "agent_thinking", "mandate_created")
            data: Event data payload
            event_id: Optional unique event ID for client tracking

        Events are queued and delivered via get_events_stream().
        If session doesn't exist, it's created automatically.
        """
        async with self._lock:
            # Create session if it doesn't exist
            if session_id not in self._queues:
                await self.create_session(session_id)

            # Update last activity
            if session_id in self._sessions:
                self._sessions[session_id]["last_activity"] = datetime.utcnow()

        # Construct event object
        event = {
            "type": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if event_id:
            event["id"] = event_id

        # Add to queue (non-blocking)
        try:
            await self._queues[session_id].put(event)
            logger.debug(f"Added event to session {session_id}: {event_type}")
        except Exception as e:
            logger.error(f"Failed to add event to session {session_id}: {e}")

    async def get_events_stream(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        """
        Get async event stream for a session.

        Args:
            session_id: Session identifier

        Yields:
            Event dictionaries from the session queue

        This is used by the SSE endpoint to stream events to the client.
        Blocks until events are available or session is closed.
        """
        # Create session if it doesn't exist
        if session_id not in self._queues:
            await self.create_session(session_id)

        queue = self._queues[session_id]

        try:
            while True:
                # Wait for next event (blocks until available)
                event = await queue.get()

                # None is sentinel value for session close
                if event is None:
                    logger.info(f"Session stream closed: {session_id}")
                    break

                yield event

        except asyncio.CancelledError:
            logger.info(f"Session stream cancelled: {session_id}")
            raise

        except Exception as e:
            logger.error(f"Error in event stream for session {session_id}: {e}")
            raise

    async def close_session(self, session_id: str) -> None:
        """
        Close a session and clean up resources.

        Args:
            session_id: Session to close

        Sends None sentinel to stream, removes queue and metadata.
        """
        async with self._lock:
            if session_id in self._queues:
                # Send close sentinel
                try:
                    await self._queues[session_id].put(None)
                except Exception as e:
                    logger.warning(f"Error sending close sentinel to {session_id}: {e}")

                # Remove from tracking
                del self._queues[session_id]
                if session_id in self._sessions:
                    del self._sessions[session_id]

                logger.info(f"Closed SSE session: {session_id}")

    async def cleanup_inactive_sessions(self) -> None:
        """
        Remove sessions that have been inactive beyond timeout threshold.

        Called periodically to prevent memory leaks from abandoned sessions.
        """
        now = datetime.utcnow()
        to_remove = []

        async with self._lock:
            for session_id, metadata in self._sessions.items():
                last_activity = metadata["last_activity"]
                if now - last_activity > self._session_timeout:
                    to_remove.append(session_id)

        # Close inactive sessions
        for session_id in to_remove:
            logger.info(f"Cleaning up inactive session: {session_id}")
            await self.close_session(session_id)

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} inactive sessions")

    def get_active_session_count(self) -> int:
        """Get number of active sessions."""
        return len(self._queues)

    def get_session_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session metadata.

        Args:
            session_id: Session identifier

        Returns:
            Session info dict or None if not found
        """
        if session_id in self._sessions:
            metadata = self._sessions[session_id]
            return {
                "session_id": session_id,
                "created_at": metadata["created_at"].isoformat(),
                "last_activity": metadata["last_activity"].isoformat(),
                "queue_size": self._queues[session_id].qsize(),
            }
        return None


# Global SSE manager instance
_sse_manager: Optional[SSEManager] = None


def get_sse_manager() -> SSEManager:
    """
    Get or create global SSE manager instance.

    Returns:
        SSEManager singleton
    """
    global _sse_manager
    if _sse_manager is None:
        _sse_manager = SSEManager(session_timeout_minutes=30)
    return _sse_manager


async def start_cleanup_task():
    """
    Start background task for periodic session cleanup.

    Should be called during application startup.
    Runs cleanup every 5 minutes.
    """
    manager = get_sse_manager()
    while True:
        await asyncio.sleep(300)  # 5 minutes
        try:
            await manager.cleanup_inactive_sessions()
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}")
