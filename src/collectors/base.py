"""Base collector abstract class for pluggable data collectors."""
from __future__ import annotations

import sqlite3
from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseCollector(ABC):
    """Abstract base for data collectors."""

    @abstractmethod
    def collect(self, conn: sqlite3.Connection,
                items: Optional[List[str]] = None,
                cities: Optional[List[str]] = None) -> int:
        """
        Collect data and write to DB.
        Returns the number of records inserted.
        """
        ...

    @abstractmethod
    def cleanup_old_data(self, conn: sqlite3.Connection,
                         max_hours_old: int = 48) -> int:
        """Remove entries older than max_hours_old hours."""
        ...


class MarketPricesCollector(BaseCollector):
    """Collects sell/buy order prices from AlbionOnlineData API."""

    def __init__(self, db_path: str):
        try:
            from src.db.engine import DatabaseEngine
        except ImportError:
            from albion_strategist_refactor.db.engine import DatabaseEngine
        self.db_path = db_path

    def collect(self, conn: sqlite3.Connection,
                items: Optional[List[str]] = None,
                cities: Optional[List[str]] = None) -> int:
        """Fetch current market prices for filtered items."""
        try:
            from src.config.settings import settings
        except ImportError:
            from albion_strategist_refactor.config.settings import settings
        try:
            from src.api.client import AlbionOnlineClient
        except ImportError:
            from albion_strategist_refactor.api.client import AlbionOnlineClient

        if items is None:
            items = settings.filtered_items

        if cities is None:
            cities = [c.name for c in settings.available_cities]

        client = AlbionOnlineClient(
            base_url=settings.api_host,
            timeout=settings.api_timeout,
            retry_count=settings.api_retry_count,
            retry_delay=settings.api_retry_delay,
        )

        cursor = conn.cursor()
        inserted = 0
        batch_size = 50

        cities_str = [c if isinstance(c, str) else getattr(c, "name", str(c)) for c in cities]

        for i in range(0, len(items), batch_size):
            batch_items = items[i:i + batch_size]
            try:
                price_records = client.get_prices_batch(batch_items, cities_str)
                from datetime import datetime, timezone
                ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

                for rec in price_records:
                    item_name = rec.get("item_id")
                    city_name = rec.get("city")
                    quality = rec.get("quality", 0)
                    sell_min = rec.get("sell_price_min", 0)
                    buy_max = rec.get("buy_price_max", 0)

                    sell_date = rec.get("sell_price_min_date") or ts
                    buy_date = rec.get("buy_price_max_date") or ts

                    if not item_name or not city_name:
                        continue

                    # 1. Update latest price snapshot (independent sell/buy timestamps)
                    cursor.execute("""
                        INSERT INTO market_prices
                        (item_unique_name, city_name, quality, sell_price_min, buy_price_max, timestamp, sell_updated_at, buy_updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(item_unique_name, city_name, quality) DO UPDATE SET
                            sell_price_min = excluded.sell_price_min,
                            buy_price_max = excluded.buy_price_max,
                            timestamp = excluded.timestamp,
                            sell_updated_at = excluded.sell_updated_at,
                            buy_updated_at = excluded.buy_updated_at
                    """, (item_name, city_name, quality, sell_min, buy_max, ts, sell_date, buy_date))

                    # 2. Record historical time-series log (for price history charts & trends)
                    cursor.execute("""
                        INSERT INTO market_price_history
                        (item_unique_name, city_name, quality, sell_price_min, buy_price_max, sell_updated_at, buy_updated_at, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item_name, city_name, quality, sell_min, buy_max, sell_date, buy_date, ts))

                    inserted += 1

            except Exception as e:
                print(f"[!] Error in batch price collection: {e}")

        if inserted > 0:
            conn.commit()
            print(f"[+] Inserted/updated {inserted} price records")

        return inserted

    def cleanup_old_data(self, conn: sqlite3.Connection,
                         max_hours_old: int = 48) -> int:
        """Remove stale history entries older than max_hours_old hours."""
        from datetime import datetime, timedelta, timezone
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=max_hours_old)
                  ).strftime("%Y-%m-%dT%H:%M:%S")
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM market_price_history WHERE recorded_at < ?", (cutoff,)
        )
        deleted = cursor.rowcount
        conn.commit()
        if deleted > 0:
            print(f"[🧹] Cleanup: removed {deleted} stale history entries (> {max_hours_old}h)")
        return deleted


class CatalogSyncCollector(BaseCollector):
    """Synchronizes items.json → database."""

    def __init__(self, db_path: str, items_json_file: str,
                 world_json_file: str):
        self.db_path = db_path
        self.items_json_file = items_json_file
        self.world_json_file = world_json_file

    def collect(self, conn: sqlite3.Connection,
                items: Optional[List[str]] = None,
                cities: Optional[List[str]] = None) -> int:
        """Parse items.json and upsert into DB."""
        if not __import__("os").path.exists(self.items_json_file):
            print(f"[!] {self.items_json_file} not found. Skip catalog sync.")
            return 0

        import json
        with open(self.items_json_file, "r", encoding="utf-8") as f:
            items_data = json.load(f)

        cursor = conn.cursor()
        inserted = 0

        for entry in items_data:
            unique_name = entry.get("UniqueName", "")
            if not unique_name:
                continue

            en_name = None
            ru_name = None
            if entry.get("LocalizedNames"):
                en_name = entry["LocalizedNames"].get("EN-US")
                ru_name = entry["LocalizedNames"].get("RU-RU")

            item_type, tier, enchant = self._parse_unique_name(unique_name)

            cursor.execute("""
                INSERT OR REPLACE INTO items
                (unique_name, en_name, ru_name, item_type, tier, enchantment, json_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (unique_name, en_name, ru_name, item_type, tier, enchant,
                  json.dumps(entry, ensure_ascii=False)))
            inserted += 1

        conn.commit()
        print(f"[+] Catalog sync: inserted {inserted} items")
        return inserted

    @staticmethod
    def _parse_unique_name(name: str):
        """Parse TIER_TYPE@ENCHANTMENT from UniqueName."""
        parts = name.split("_")
        item_type = name
        tier = 0
        enchant = 0

        if len(parts) > 1 and parts[0].startswith("T"):
            try:
                tier = int(parts[0][1:])
                for part in parts[1:]:
                    if "@" in part:
                        item_type_parts = []
                        for p in parts[1:]:
                            if "@" not in p:
                                item_type_parts.append(p)
                            else:
                                item_type_parts.append(p.split("@")[0])
                                try:
                                    enchant = int(p.split("@")[1])
                                except ValueError:
                                    pass
                        item_type = "_".join(item_type_parts)
                        break
                    else:
                        item_type = "_".join(parts[1:])
            except ValueError:
                item_type = name

        return item_type, tier, enchant

    def cleanup_old_data(self, conn: sqlite3.Connection,
                         max_hours_old: int = 48) -> int:
        """Catalog doesn't have timestamps — no-op."""
        return 0


def collect_once(db_path: str) -> int:
    """Run a single price collection and cleanup cycle."""
    from src.db.engine import DatabaseEngine
    from src.config.settings import settings

    engine = DatabaseEngine(db_path)

    # 1. Cleanup old history entries
    with engine.session() as conn:
        collector = MarketPricesCollector(db_path)
        collector.cleanup_old_data(conn, max_hours_old=settings.max_data_age_hours)

    # 2. Collect market prices
    with engine.session() as conn:
        collector = MarketPricesCollector(db_path)
        inserted = collector.collect(conn)

    engine.close()
    return inserted
