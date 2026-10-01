#!/usr/bin/env python3
"""
Albion Market Data Collector — updated entry point.
Uses the new modular architecture: config, api, db, collectors.

Usage:
    python albion_data_collector.py [--interval N]
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Automatically discover and attach project root to sys.path
def _ensure_project_root():
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        if (curr / "pyproject.toml").exists() or (curr / ".git").exists():
            root_str = str(curr)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            return
        curr = curr.parent
_ensure_project_root()

# Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("collector")

from src.config.settings import settings
from src.collectors.base import MarketPricesCollector, collect_once
from src.db.engine import DatabaseEngine


def collect_once(db_path: str) -> int:
    """Run one collection cycle and return inserted count."""
    engine = DatabaseEngine(db_path)

    # 1. Cleanup old data BEFORE collection
    with engine.session() as conn:
        collector = MarketPricesCollector(db_path)
        collector.cleanup_old_data(conn, max_hours_old=settings.max_data_age_hours)

    # 2. Collect new prices
    with engine.session() as conn:
        collector = MarketPricesCollector(db_path)
        inserted = collector.collect(conn)

    engine.close()
    return inserted


def collect_loop(db_path: str, interval: int = 300):
    """Run collection in a loop."""
    logger.info(f"[+] Collector started. Interval: {interval}s")
    print(f"[+] Фоновый планировщик запущен. Интервал обновления: {interval} сек.")

    while True:
        try:
            print(f"\n[->] Запуск планового сбора цен ({time.strftime('%Y-%m-%d %H:%M:%S')})...")
            inserted = collect_once(db_path)
            print(f"[<-] Плановый сбор успешно завершен. Вставлено: {inserted} записей.")
        except Exception as e:
            logger.error(f"[!] Ошибка планового сбора: {e}")

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="Albion Market Data Collector")
    parser.add_argument("--interval", type=int, default=settings.scheduler_interval,
                        help="Interval in seconds between collections")
    args = parser.parse_args()

    if args.interval <= 0:
        # One-shot mode
        inserted = collect_once(settings.db_path)
        logger.info(f"One-shot complete: {inserted} records inserted")
    else:
        # Loop mode
        collect_loop(settings.db_path, interval=args.interval)


if __name__ == "__main__":
    main()
