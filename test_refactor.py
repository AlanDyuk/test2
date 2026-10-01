#!/usr/bin/env python3
"""Test suite for albion_market_strategist refactor."""
import sys, os, tempfile, traceback

sys.path.insert(0, "/tmp/albion_strategist_refactor")

print("="*60)
print("ALBION MARKET STRATEGIST - REFRACTOR TEST")
print("="*60)

print("\n=== TEST 1: Module Imports ===")
modules = [
    "config.settings",
    "api.models",
    "api.client",
    "db.engine",
    "collectors.base",
    "services.item_categorizer",
    "services.trade_analyzer",
    "services.scheduler",
    "auth.password_manager",
    "workers.price_collector",
]
for mod in modules:
    try:
        __import__(mod)
        print(f"  ✅ {mod}")
    except Exception as e:
        print(f"  ❌ {mod}: {e}")

print("\n=== TEST 2: Settings ===")
from config.settings import settings
try:
    print(f"  ✅ app_name: {settings.app_name}")
    print(f"  ✅ api_host: {settings.api_host}")
    print(f"  ✅ timeout: {settings.api_timeout}")
    print(f"  ✅ cities: {[c.name for c in settings.available_cities]}")
except Exception as e:
    print(f"  ❌ Settings: {e}")

print("\n=== TEST 3: PasswordManager ===")
from auth.password_manager import PasswordManager
try:
    pm = PasswordManager()
    h = pm.hash_password("test123")
    assert pm.verify("test123", h), "verify failed"
    assert not pm.verify("wrong", h), "should fail"
    print(f"  ✅ hash: {h[:40]}...")
    print(f"  ✅ verify correct: True")
    print(f"  ✅ verify wrong: False")
except Exception as e:
    print(f"  ❌ PasswordManager: {e}")

print("\n=== TEST 4: DatabaseEngine ===")
from db.engine import DatabaseEngine
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        engine = DatabaseEngine(db_path)
        with engine.session() as conn:
            conn.execute(
                "INSERT INTO items (unique_name, en_name) VALUES (?, ?)",
                ("T3_WOOD", "Wood"),
            )
            conn.execute(
                "INSERT INTO items (unique_name, en_name) VALUES (?, ?)",
                ("T4_ORE", "Iron Ore"),
            )
            conn.execute(
                "INSERT INTO items (unique_name, en_name) VALUES (?, ?)",
                ("T5_BAG", "Bag"),
            )
            conn.commit()
        engine.close()
    print("  ✅ DatabaseEngine (create, insert, migrate)")
except Exception as e:
    print(f"  ❌ DatabaseEngine: {e}")

print("\n=== TEST 5: TradeAnalyzer ===")
from services.trade_analyzer import get_trade_opportunities
try:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        engine = DatabaseEngine(db_path)
        conn = engine.connect()
        conn.execute(
            "INSERT OR REPLACE INTO market_prices "
            "(item_unique_name, city_name, quality, sell_price_min, buy_price_max, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("T4_ORE", "Martlock", 1, 100, 80, "2026-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO market_prices "
            "(item_unique_name, city_name, quality, sell_price_min, buy_price_max, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("T4_ORE", "Thetford", 1, 150, 130, "2026-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO market_prices "
            "(item_unique_name, city_name, quality, sell_price_min, buy_price_max, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("T5_BAG", "Martlock", 1, 500, 400, "2026-01-01T00:00:00"),
        )
        conn.execute(
            "INSERT OR REPLACE INTO market_prices "
            "(item_unique_name, city_name, quality, sell_price_min, buy_price_max, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("T5_BAG", "Caerleon", 1, 700, 600, "2026-01-01T00:00:00"),
        )
        conn.commit()
        results = get_trade_opportunities(
            db_path=db_path,
            tracked_items=["T4_ORE", "T5_BAG"],
            target_cities=["Martlock", "Thetford", "Caerleon"],
            has_premium=True,
            max_hours_old=24,
            trade_mode="order_flip",
        )
        engine.close()
        print(f"  ✅ Found {len(results)} trade opportunities")
        for r in results[:5]:
            print(
                f"     {r['item']}: "
                f"{r['buy_city']}@{r['buy_price']:.0f} -> "
                f"{r['sell_city']}@{r['sell_price']:.0f} "
                f"= +{r['net_profit']:.0f} ({r['profit_percentage']:.1f}%)"
            )
except Exception as e:
    traceback.print_exc()
    print(f"  ❌ TradeAnalyzer: {e}")

print("\n=== TEST 6: ItemCategorizer ===")
from services.item_categorizer import get_categorized_items, filter_resource_items
try:
    cat = get_categorized_items("nonexistent.json")
    total = sum(len(v) for v in cat.values())
    print(f"  ✅ get_categorized_items: {len(cat)} main, {total} sub categories")
except Exception as e:
    print(f"  ❌ get_categorized_items: {e}")

try:
    items = filter_resource_items("items.json")
    print(f"  ✅ filter_resource_items: {len(items)} resources")
    print(f"     First 5: {items[:5]}")
except Exception as e:
    print(f"  ❌ filter_resource_items: {e}")

print("\n=== TEST 7: Scheduler (cross-platform) ===")
from services.scheduler import Scheduler
try:
    s = Scheduler()
    assert s.is_running() == False, "should not be running"
    s.cleanup_stale_pid()
    print("  ✅ Scheduler (psutil-based, cross-platform)")
except Exception as e:
    print(f"  ❌ Scheduler: {e}")

print("\n=== TEST 8: API Client (connection test) ===")
from api.client import AlbionOnlineClient
try:
    client = AlbionOnlineClient(
        base_url="https://east.albion-online-data.com",
        timeout=5.0,
    )
    cities = client.get_cities()
    if isinstance(cities, list) and len(cities) > 0:
        print(f"  ✅ API connection: {len(cities)} cities fetched")
        print(f"     Sample: {cities[0]['name'] if 'name' in cities[0] else cities[0]}")
    else:
        print(f"  ⚠️ API returned empty: {type(cities)}")
except Exception as e:
    print(f"  ❌ API Client: {e}")

print("\n" + "="*60)
print("ALL TESTS COMPLETED")
print("="*60)
