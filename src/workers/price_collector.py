"""Background worker for native price collection."""
from __future__ import annotations

import logging
import os
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

logger = logging.getLogger(__name__)


class PriceCollectorWorker:
    """Worker that directly runs MarketPricesCollector natively in Python."""

    def __init__(self, db_path: str = "albion_market.db", interval_seconds: int = 300):
        self.db_path = db_path
        self.interval = interval_seconds
        self._running = False

    def run_once(self) -> int:
        """Execute a single collection cycle natively in Python."""
        from src.collectors.base import collect_once
        return collect_once(self.db_path)

    def start(self) -> None:
        """Run the native collection loop (blocking)."""
        self._running = True
        logger.info(f"[+] PriceCollectorWorker started natively. Interval: {self.interval}s")

        while self._running:
            try:
                logger.info(f"[->] Scheduled native price collection at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                inserted = self.run_once()
                logger.info(f"[<-] Collection complete: {inserted} records inserted/updated")
            except Exception as e:
                logger.error(f"[!] Collection error: {e}")

            time.sleep(self.interval)

        logger.info("[+] PriceCollectorWorker stopped")

    def stop(self) -> None:
        """Signal worker to stop."""
        self._running = False
