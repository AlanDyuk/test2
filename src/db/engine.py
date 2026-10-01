"""Database engine and connection management."""
from __future__ import annotations

import logging
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger(__name__)


class DatabaseEngine:
    """SQLite connection engine with auto-migration and thread safety."""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._lock = threading.Lock()
        self._session_lock = threading.Lock()

    def connect(self) -> sqlite3.Connection:
        """Get or create a database connection."""
        with self._lock:
            if self._conn is None:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
                self._conn = sqlite3.connect(
                    str(self.db_path),
                    check_same_thread=False,
                    timeout=30.0,
                )
                self._conn.row_factory = sqlite3.Row
                # Enable WAL mode for better concurrency
                self._conn.execute("PRAGMA journal_mode=WAL")
                # Enable foreign keys
                self._conn.execute("PRAGMA foreign_keys=ON")
                # Migrate schema
                self._migrate_unlocked()
                logger.info(f"Connected to {self.db_path}")
            return self._conn

    def close(self):
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    @contextmanager
    def session(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager for a thread-safe database session."""
        with self._session_lock:
            conn = self.connect()
            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def migrate(self):
        """Apply all schema migrations."""
        with self._lock:
            self._migrate_unlocked()

    def _migrate_unlocked(self):
        """Internal migration logic called with lock acquired."""
        if self._conn is None:
            return
        conn = self._conn
        cursor = conn.cursor()

        # Version table for tracking migrations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        current_version = 0
        for row in cursor.execute("SELECT MAX(version) FROM _migrations"):
            v = row[0]
            current_version = v if v else 0

        # Migration v1: base tables
        if current_version < 1:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    unique_name TEXT PRIMARY KEY,
                    en_name TEXT,
                    ru_name TEXT,
                    item_type TEXT,
                    tier INTEGER DEFAULT 0,
                    enchantment INTEGER DEFAULT 0,
                    json_data TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_prices (
                    item_unique_name TEXT NOT NULL,
                    city_name TEXT NOT NULL,
                    quality INTEGER NOT NULL,
                    sell_price_min REAL,
                    buy_price_max REAL,
                    timestamp TEXT NOT NULL,
                    PRIMARY KEY (item_unique_name, city_name, quality)
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_market_prices_timestamp "
                "ON market_prices(timestamp)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_market_prices_item "
                          "ON market_prices(item_unique_name)")
            cursor.execute(
                "INSERT OR IGNORE INTO _migrations (version) VALUES (1)"
            )

        # Migration v2: add city_en and quality display fields
        if current_version < 2:
            try:
                cursor.execute("ALTER TABLE market_prices ADD COLUMN quality_display TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            cursor.execute(
                "INSERT OR IGNORE INTO _migrations (version) VALUES (2)"
            )

        # Migration v3: Independent buy/sell timestamps + Historical time-series table
        if current_version < 3:
            try:
                cursor.execute("ALTER TABLE market_prices ADD COLUMN sell_updated_at TEXT")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE market_prices ADD COLUMN buy_updated_at TEXT")
            except sqlite3.OperationalError:
                pass

            # Create market_price_history table for true time-series data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_unique_name TEXT NOT NULL,
                    city_name TEXT NOT NULL,
                    quality INTEGER NOT NULL,
                    sell_price_min REAL,
                    buy_price_max REAL,
                    sell_updated_at TEXT,
                    buy_updated_at TEXT,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_item_city "
                "ON market_price_history(item_unique_name, city_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_history_recorded "
                "ON market_price_history(recorded_at)"
            )
            cursor.execute(
                "INSERT OR IGNORE INTO _migrations (version) VALUES (3)"
            )

        conn.commit()
        logger.info("Database migrations applied (current: v3)")
