"""Bootstrap and health diagnostics module."""
from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger("bootstrap")


def _get_project_root() -> Path:
    """Find absolute project root directory."""
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        if (curr / "pyproject.toml").exists() or (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent.parent


PROJECT_ROOT = _get_project_root()


def ensure_sys_path():
    """Ensure project root is on sys.path[0]."""
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


ensure_sys_path()

from src.config.settings import settings
from src.db.engine import DatabaseEngine
from src.auth.password_manager import PasswordManager


class SystemHealthCheck:
    """Health check and self-healing environment bootstrapped."""

    def __init__(self):
        self.root = PROJECT_ROOT

    def run_diagnostics(self) -> Dict[str, Any]:
        """Run complete environment and integrity verification."""
        results = {
            "root_path": str(self.root),
            "env_file": False,
            "db_status": False,
            "db_version": 0,
            "tracked_items_count": 0,
            "target_cities_count": 0,
            "api_reachable": False,
        }

        # 1. Environment .env verification
        env_path = self.root / ".env"
        env_example = self.root / ".env.example"

        if not env_path.exists() and env_example.exists():
            logger.info("📄 .env missing, copying from .env.example...")
            env_path.write_text(env_example.read_text(encoding="utf-8"), encoding="utf-8")

        results["env_file"] = env_path.exists()

        # 2. Database verification & migrations
        try:
            engine = DatabaseEngine(settings.db_path)
            conn = engine.connect()
            cursor = conn.cursor()
            
            v = cursor.execute("SELECT MAX(version) FROM _migrations").fetchone()[0]
            results["db_version"] = v or 0
            results["db_status"] = True
            engine.close()
        except Exception as e:
            logger.error(f"❌ DB initialization error: {e}")
            results["db_status"] = False

        # 3. Tracked items & cities files
        results["tracked_items_count"] = len(settings.filtered_items)
        results["target_cities_count"] = len(settings.target_cities)

        # 4. API Reachability check
        try:
            from src.api.client import AlbionOnlineClient
            with AlbionOnlineClient(settings.api_host, timeout=5.0) as client:
                res = client.get_prices_batch(["T3_WOOD"], ["Martlock"])
                results["api_reachable"] = isinstance(res, list)
        except Exception as e:
            logger.warning(f"⚠️ API check warning: {e}")
            results["api_reachable"] = False

        return results

    def self_heal(self) -> bool:
        """Run self-healing routines to prepare application for launch."""
        logger.info("🔧 Running system self-healing...")
        
        # 1. Initialize DB schema
        engine = DatabaseEngine(settings.db_path)
        engine.connect()
        engine.close()

        # 2. Populate filtered items if missing
        if not settings.filtered_items:
            logger.info("📦 Population initial resource tracking filter...")
            from src.services.item_categorizer import filter_resource_items, save_filtered_items
            items = filter_resource_items(settings.items_json_file)
            save_filtered_items(items, settings.filtered_items_file)
            settings.filtered_items = items

        # 3. Hash plaintext password if set in .env
        pm = PasswordManager()
        pm.check_password_file(str(self.root / ".env"))

        return True
