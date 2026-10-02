"""Comprehensive unit & regression test suite for Albion Market Strategist Pro."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.auth.password_manager import PasswordManager
from src.config.settings import AppSettings
from src.db.engine import DatabaseEngine
from src.services.trade_analyzer import analyze_trades


class TestAlbionMarketStrategist(unittest.TestCase):
    """Unit tests for core services, database migrations, and domain logic."""

    def setUp(self):
        """Set up a temporary database in memory for isolated test cases."""
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmp_dir.name, "test_market.db")
        self.engine = DatabaseEngine(self.db_path)
        self.conn = self.engine.connect()

    def tearDown(self):
        """Clean up database connection and temporary directory."""
        self.engine.close()
        self.tmp_dir.cleanup()

    def _insert_price(self, item="T4_BAG", city="Martlock", quality=1,
                      sell_min=5000, buy_max=4000,
                      sell_updated_at=None, buy_updated_at=None):
        """Helper to seed market_prices snapshot table."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        s_date = sell_updated_at or ts
        b_date = buy_updated_at or ts

        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO market_prices
            (item_unique_name, city_name, quality, sell_price_min, buy_price_max, timestamp, sell_updated_at, buy_updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (item, city, quality, sell_min, buy_max, ts, s_date, b_date))
        self.conn.commit()

    def test_zero_price_exclusion(self):
        """Assert that prices with 0 silver (no market data) are excluded."""
        # City A has 0 sell price (no sell orders)
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=0, buy_max=2000)
        # City B has normal sell price
        self._insert_price(item="T4_BAG", city="Thetford", sell_min=6000, buy_max=3000)

        trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], max_hours_old=24)
        # Should be 0 trades because buy_price from Martlock sell_min is 0 (invalid)
        self.assertEqual(len(trades), 0)

    def test_stale_buy_price_exclusion(self):
        """Assert that stale buy prices older than max_hours_old are excluded."""
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%S")
        fresh_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        # Stale buy price in Martlock (10h old)
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=3000, sell_updated_at=old_ts)
        # Fresh sell price in Thetford (0h old)
        self._insert_price(item="T4_BAG", city="Thetford", sell_min=6000, sell_updated_at=fresh_ts)

        # Max hours old = 6h -> Martlock price should be rejected
        trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], max_hours_old=6)
        self.assertEqual(len(trades), 0)

    def test_stale_sell_price_exclusion(self):
        """Assert that stale sell prices older than max_hours_old are excluded."""
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=10)).strftime("%Y-%m-%dT%H:%M:%S")
        fresh_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

        # Fresh buy price in Martlock (0h old)
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=3000, sell_updated_at=fresh_ts)
        # Stale sell price in Thetford (10h old)
        self._insert_price(item="T4_BAG", city="Thetford", sell_min=6000, sell_updated_at=old_ts)

        trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], max_hours_old=6)
        self.assertEqual(len(trades), 0)

    def test_same_city_trade_exclusion(self):
        """Assert that trades within the exact same city are excluded."""
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=3000, buy_max=5000)

        trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], target_cities=["Martlock"])
        self.assertEqual(len(trades), 0)

    def test_negative_profit_exclusion(self):
        """Assert that trades resulting in negative net profit are excluded."""
        # Buy in Martlock at 5000, Sell in Thetford at 5100 (taxes will make profit negative)
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=5000)
        self._insert_price(item="T4_BAG", city="Thetford", sell_min=5100)

        trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], has_premium=True)
        self.assertEqual(len(trades), 0)

    def test_tax_calculation_premium(self):
        """Assert correct tax rate calculation for Premium users (4.0% sales + 2.5% setup fee = 6.5%)."""
        # Buy in Martlock at 10000, Sell in Thetford at 20000
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=10000)
        self._insert_price(item="T4_BAG", city="Thetford", sell_min=20000)

        trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], has_premium=True, sales_tax_rate=0.040, trade_mode="order_flip")
        self.assertEqual(len(trades), 1)

        trade = trades[0]
        # Total tax = 6.5% -> net sell = 20000 * 0.935 = 18700 -> net profit = 8700
        self.assertAlmostEqual(trade["tax_rate"], 6.5)
        self.assertAlmostEqual(trade["net_profit"], 8700.0)

    def test_tax_calculation_standard(self):
        """Assert correct tax rate calculation for Standard (non-Premium) users (8.0% + 2.5% = 10.5%)."""
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=10000)
        self._insert_price(item="T4_BAG", city="Thetford", sell_min=20000)

        trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], has_premium=False, sales_tax_rate=0.080, trade_mode="order_flip")
        self.assertEqual(len(trades), 1)

        trade = trades[0]
        # Total tax = 10.5% -> net sell = 20000 * 0.895 = 17900 -> net profit = 7900
        self.assertAlmostEqual(trade["tax_rate"], 10.5)
        self.assertAlmostEqual(trade["net_profit"], 7900.0)

    def test_trade_mode_instant_vs_order_flip(self):
        """Assert difference between 'order_flip' (sell_min) and 'instant' (buy_max)."""
        # Martlock sell_min = 10000
        self._insert_price(item="T4_BAG", city="Martlock", sell_min=10000)
        # Thetford sell_min = 20000, buy_max = 15000
        self._insert_price(item="T4_BAG", city="Thetford", sell_min=20000, buy_max=15000)

        # 1. Order Flip mode (sells at sell_min 20000)
        flip_trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], trade_mode="order_flip", has_premium=True)
        self.assertEqual(flip_trades[0]["sell_price"], 20000)

        # 2. Instant mode (sells at buy_max 15000)
        instant_trades = analyze_trades(self.conn, tracked_items=["T4_BAG"], trade_mode="instant", has_premium=True)
        self.assertEqual(instant_trades[0]["sell_price"], 15000)

    def test_database_migrations_v1_to_v3(self):
        """Assert database migration engine applies migrations v1 -> v2 -> v3 seamlessly."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT MAX(version) FROM _migrations")
        version = cursor.fetchone()[0]
        self.assertEqual(version, 3)

        # Verify columns in market_prices
        cursor.execute("PRAGMA table_info(market_prices)")
        cols = [r[1] for r in cursor.fetchall()]
        self.assertIn("sell_updated_at", cols)
        self.assertIn("buy_updated_at", cols)

        # Verify market_price_history table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='market_price_history'")
        self.assertIsNotNone(cursor.fetchone())

    def test_password_manager_bcrypt(self):
        """Assert PasswordManager uses bcrypt and validates password hashing correctly."""
        pm = PasswordManager()
        hashed = pm.hash_password("my_secret_123")

        self.assertTrue(hashed.startswith("$2b$") or hashed.startswith("$2a$"))
        self.assertTrue(pm.verify("my_secret_123", hashed))
        self.assertFalse(pm.verify("wrong_pass", hashed))


if __name__ == "__main__":
    unittest.main()
