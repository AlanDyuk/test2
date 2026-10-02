#!/usr/bin/env python3
"""
Database setup — initializes tables and applies migrations.
Kept as a standalone script for backwards compatibility.
"""
from __future__ import annotations

import sqlite3
import os
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

DB_NAME = "albion_market.db"
ITEMS_JSON = "items.json"
WORLD_JSON = "world.json"


def setup_database(db_path: str = None):
    """Initialize database schema."""
    from src.db.engine import DatabaseEngine

    path = db_path or DB_NAME
    engine = DatabaseEngine(path)

    # Ensure tables exist (backwards compatibility)
    conn = engine.connect()
    cursor = conn.cursor()

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
        CREATE TABLE IF NOT EXISTS locations (
            name TEXT PRIMARY KEY,
            en_name TEXT,
            ru_name TEXT,
            json_data TEXT
        )
    """)

    conn.commit()
    engine.close()
    print(f"[+] Database initialized at {path}")
    return path


if __name__ == "__main__":
    setup_database()
