#!/usr/bin/env python3
"""
Enable WAL Mode on Existing Databases

This script enables Write-Ahead Logging (WAL) mode on existing SQLite databases
to improve concurrency and prevent database locking issues.

Run this after the fix to enable WAL mode on existing databases:
    python backend/enable_wal_mode.py
"""
import sqlite3
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings


def enable_wal_mode(db_path: str) -> None:
    """
    Enable WAL mode on a SQLite database.
    
    Args:
        db_path: Path to the SQLite database file
    """
    if not Path(db_path).exists():
        print(f"⚠️  Database not found: {db_path}")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check current journal mode
        cursor.execute("PRAGMA journal_mode")
        current_mode = cursor.fetchone()[0]
        print(f"Current journal mode for {db_path}: {current_mode}")
        
        if current_mode.upper() == "WAL":
            print(f"✅ WAL mode already enabled for {db_path}")
        else:
            # Enable WAL mode
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.execute("PRAGMA synchronous=NORMAL")
            
            # Verify
            cursor.execute("PRAGMA journal_mode")
            new_mode = cursor.fetchone()[0]
            print(f"✅ WAL mode enabled for {db_path}: {new_mode}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Error enabling WAL mode for {db_path}: {e}")


def main():
    """Enable WAL mode on all databases."""
    print("Enabling WAL mode on databases...\n")
    
    # Main database
    main_db = settings.database_path
    print(f"Processing main database: {main_db}")
    enable_wal_mode(main_db)
    print()
    
    # Scheduler database
    scheduler_db = main_db.replace('.db', '_scheduler.db')
    print(f"Processing scheduler database: {scheduler_db}")
    enable_wal_mode(scheduler_db)
    print()
    
    print("✅ WAL mode configuration complete!")
    print("\nNote: WAL mode creates additional files (.db-wal and .db-shm)")
    print("These files are normal and part of SQLite's WAL implementation.")


if __name__ == "__main__":
    main()
