"""
Database Initialization Script

Creates SQLite database tables for GhostCart AP2 demonstration.
Tables: mandates, monitoring_jobs, transactions, sessions

AP2 Compliance: Schema matches data-model.md specification for complete
mandate chain storage and autonomous monitoring job persistence.
"""
import sqlite3
from pathlib import Path
import sys
from typing import AsyncGenerator

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker

from src.config import settings
from .models import Base


def create_tables(conn: sqlite3.Connection) -> None:
    """
    Create all database tables with indexes per data-model.md schema.

    Tables:
    - mandates: Stores Intent, Cart, Payment mandates with signatures
    - monitoring_jobs: Stores HNP monitoring job metadata
    - transactions: Stores transaction results with mandate chain links
    - sessions: Stores user session data for conversation continuity
    
    Also enables WAL mode for better concurrency.
    """
    cursor = conn.cursor()
    
    # Enable WAL mode for better concurrency (prevents most locking issues)
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
    cursor.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and performance

    # Mandates table - stores all three mandate types
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mandates (
            id TEXT PRIMARY KEY,
            mandate_type TEXT NOT NULL CHECK(mandate_type IN ('intent', 'cart', 'payment')),
            user_id TEXT NOT NULL,
            transaction_id TEXT,
            mandate_data TEXT NOT NULL,
            signer_identity TEXT NOT NULL,
            signature TEXT NOT NULL,
            signature_metadata TEXT NOT NULL,
            validation_status TEXT NOT NULL CHECK(validation_status IN ('valid', 'invalid', 'unsigned')),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for mandates
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mandates_user_id ON mandates(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mandates_transaction_id ON mandates(transaction_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mandates_type ON mandates(mandate_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mandates_created ON mandates(created_at DESC)")

    # Monitoring jobs table - for HNP autonomous monitoring
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS monitoring_jobs (
            job_id TEXT PRIMARY KEY,
            intent_mandate_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            product_query TEXT NOT NULL,
            constraints TEXT NOT NULL,
            schedule_interval_minutes INTEGER NOT NULL DEFAULT 5,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            last_check_at TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (intent_mandate_id) REFERENCES mandates(id)
        )
    """)

    # Indexes for monitoring_jobs
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_user_id ON monitoring_jobs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_active ON monitoring_jobs(active)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_monitoring_expires ON monitoring_jobs(expires_at)")

    # Transactions table - stores transaction results
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            intent_mandate_id TEXT,
            cart_mandate_id TEXT NOT NULL,
            payment_mandate_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('authorized', 'declined', 'expired', 'failed')),
            authorization_code TEXT,
            decline_reason TEXT,
            decline_code TEXT,
            amount_cents INTEGER NOT NULL,
            currency TEXT NOT NULL DEFAULT 'USD',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (intent_mandate_id) REFERENCES mandates(id),
            FOREIGN KEY (cart_mandate_id) REFERENCES mandates(id),
            FOREIGN KEY (payment_mandate_id) REFERENCES mandates(id)
        )
    """)

    # Indexes for transactions
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at DESC)")

    # Sessions table - for conversation continuity
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            current_flow_type TEXT CHECK(current_flow_type IN ('hp', 'hnp', 'none')),
            context_data TEXT,
            last_activity_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Indexes for sessions
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_activity ON sessions(last_activity_at DESC)")

    conn.commit()
    print("✅ All tables created successfully")


def initialize_database():
    """
    Initialize the database with all required tables.

    This function is called during FastAPI startup.
    """
    db_path = Path(settings.database_path)

    print(f"Initializing database at: {db_path}")

    # Create database directory if it doesn't exist
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Connect and create tables
    conn = sqlite3.connect(db_path)
    try:
        create_tables(conn)
        print(f"✅ Database initialized successfully at {db_path}")
    finally:
        conn.close()


# ============================================================================
# SQLAlchemy Async Session Setup for FastAPI
# ============================================================================

# Create async engine with optimized settings for concurrency
DATABASE_URL = f"sqlite+aiosqlite:///{settings.database_path}"
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={
        "timeout": 30,  # 30 second timeout for lock acquisition
        "check_same_thread": False
    },
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database sessions in FastAPI.

    Usage:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# Alias for FastAPI Depends
get_db = get_async_session


def main():
    """CLI entry point for initializing database."""
    initialize_database()


if __name__ == "__main__":
    main()
