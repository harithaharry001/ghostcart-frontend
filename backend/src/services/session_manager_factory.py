"""
Session Manager Factory for Strands Agents

Creates appropriate SessionManager instances based on environment configuration.
Supports file-based and S3-based session storage.

AP2 Protocol Context:
- Session persistence for multi-turn conversations
- Per-agent conversation history management
- Automatic context loading/saving via Strands SDK
"""
from strands.session import FileSessionManager, S3SessionManager, SessionManager
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)


def create_session_manager(
    session_id: str,
    storage_dir: Optional[str] = None,
    storage_type: Optional[str] = None
) -> SessionManager:
    """
    Create a SessionManager for the given session.

    Uses environment variables to determine storage backend:
    - SESSION_STORAGE_TYPE: "file" (default) or "s3"
    - SESSION_STORAGE_DIR: Directory for file storage (default: ./.sessions)
    - SESSION_S3_BUCKET: S3 bucket name (required if storage_type=s3)
    - SESSION_S3_PREFIX: S3 key prefix (default: sessions/)

    Args:
        session_id: Unique session identifier
        storage_dir: Override directory for file storage
        storage_type: Override storage type ("file" or "s3")

    Returns:
        Configured SessionManager instance (FileSessionManager or S3SessionManager)

    Example (File Storage):
        session_mgr = create_session_manager("sess_abc123")

        agent = Agent(
            model=model,
            tools=[...],
            session_manager=session_mgr
        )

    Example (S3 Storage):
        # Set environment variables:
        # SESSION_STORAGE_TYPE=s3
        # SESSION_S3_BUCKET=ghostcart-sessions

        session_mgr = create_session_manager("sess_abc123")

    Storage Structure (File):
        ./.sessions/
        └── session_sess_abc123/
            ├── session.json                # Session metadata
            └── agents/
                └── agent_supervisor_001/
                    ├── agent.json          # Agent metadata
                    └── messages/
                        ├── message_001.json
                        └── message_002.json

    Storage Structure (S3):
        s3://ghostcart-sessions/
        └── sessions/
            └── session_sess_abc123/
                ├── session.json
                └── agents/
                    └── agent_supervisor_001/
                        ├── agent.json
                        └── messages/
                            ├── message_001.json
                            └── message_002.json
    """
    # Determine storage type
    if storage_type is None:
        storage_type = os.environ.get('SESSION_STORAGE_TYPE', 'file').lower()

    if storage_type == 's3':
        # S3 storage for production/distributed systems
        bucket = os.environ.get('SESSION_S3_BUCKET')
        if not bucket:
            logger.warning(
                "SESSION_S3_BUCKET not set, falling back to file storage"
            )
            storage_type = 'file'
        else:
            prefix = os.environ.get('SESSION_S3_PREFIX', 'sessions/')
            logger.info(
                f"Creating S3 session manager: session_id={session_id}, "
                f"bucket={bucket}, prefix={prefix}"
            )
            return S3SessionManager(
                session_id=session_id,
                bucket=bucket,
                prefix=prefix
            )

    # File storage (default) for dev/single-server
    if storage_dir is None:
        storage_dir = os.environ.get('SESSION_STORAGE_DIR', './.sessions')

    logger.info(
        f"Creating file session manager: session_id={session_id}, "
        f"storage_dir={storage_dir}"
    )
    return FileSessionManager(
        session_id=session_id,
        storage_dir=storage_dir
    )


def cleanup_old_sessions(
    storage_dir: Optional[str] = None,
    max_age_days: int = 7
) -> int:
    """
    Clean up session files older than max_age_days.

    This is a maintenance function to prevent session storage from growing unbounded.
    Should be called periodically (e.g., daily cron job).

    Args:
        storage_dir: Directory containing session files
        max_age_days: Maximum age of sessions to keep (default: 7 days)

    Returns:
        Number of sessions deleted

    Example:
        # Delete sessions older than 7 days
        deleted_count = cleanup_old_sessions()
        logger.info(f"Cleaned up {deleted_count} old sessions")
    """
    import shutil
    from datetime import datetime, timedelta
    from pathlib import Path

    if storage_dir is None:
        storage_dir = os.environ.get('SESSION_STORAGE_DIR', './.sessions')

    storage_path = Path(storage_dir)
    if not storage_path.exists():
        return 0

    cutoff_time = datetime.now() - timedelta(days=max_age_days)
    deleted_count = 0

    for session_dir in storage_path.iterdir():
        if not session_dir.is_dir():
            continue

        # Check session modification time
        mtime = datetime.fromtimestamp(session_dir.stat().st_mtime)
        if mtime < cutoff_time:
            logger.info(f"Deleting old session: {session_dir.name}")
            shutil.rmtree(session_dir)
            deleted_count += 1

    return deleted_count
