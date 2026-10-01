#!/usr/bin/env python3
"""
Albion Market Strategist Pro — Unified Production Launcher & Bootstrapper.
Manages system health checks, database migrations, scheduler & Streamlit orchestration.
"""
from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Fix sys.path to ensure src package is always importable
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("launcher")

from src.bootstrap.health import SystemHealthCheck
from src.config.settings import settings


def print_banner():
    """Print ASCII application banner."""
    print("=" * 65)
    print(" ⚔️  ALBION MARKET STRATEGIST PRO — LAUNCHER & BOOTSTRAPPER")
    print("=" * 65)


def run_check():
    """Execute complete health check and print report."""
    print_banner()
    logger.info("🔍 Running system diagnostics...")
    hc = SystemHealthCheck()
    report = hc.run_diagnostics()

    print("\n--- DIAGNOSTIC REPORT ---")
    print(f"  • Root Directory:        {report['root_path']}")
    print(f"  • Environment (.env):    {'🟢 OK' if report['env_file'] else '❌ Missing'}")
    print(f"  • Database (SQLite v{report['db_version']}): {'🟢 Active' if report['db_status'] else '❌ Error'}")
    print(f"  • Tracked Items:        {report['tracked_items_count']} items")
    print(f"  • Target Cities:        {report['target_cities_count']} cities")
    print(f"  • Albion API Connection: {'🟢 Reachable' if report['api_reachable'] else '⚠️ Unreachable / Offline'}")
    print("-" * 65 + "\n")


import socket

def _find_available_port(start_port: int, address: str = "0.0.0.0") -> int:
    """Find a free TCP port starting from start_port."""
    port = start_port
    while port < start_port + 50:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((address if address != "0.0.0.0" else "", port))
                return port
            except OSError:
                port += 1
    return start_port


def launch_server(address: str = "0.0.0.0", port: int = 8501, is_headless: bool = False):
    """Launch Streamlit web UI & background price scheduler."""
    print_banner()
    
    # Check and select available port automatically
    actual_port = _find_available_port(port, address)
    if actual_port != port:
        logger.warning(f"⚠️ Port {port} is occupied. Automatically switched to free port {actual_port}!")
    port = actual_port

    # 1. Self-healing environment check
    hc = SystemHealthCheck()
    hc.self_heal()

    # Set env vars for child subprocesses
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")

    # 2. Start Background Price Scheduler
    from src.services.scheduler import Scheduler
    scheduler = Scheduler(settings.pid_file)
    if not scheduler.is_running():
        logger.info("🔄 Starting background price collection scheduler...")
        scheduler.start(interval=settings.scheduler_interval, collector_script="albion_data_collector.py")

    # 3. Launch Streamlit Web UI
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(PROJECT_ROOT / "src" / "ui" / "streamlit" / "main.py"),
        "--server.port", str(port),
        "--server.address", address,
    ]

    if is_headless:
        cmd.extend(["--server.headless", "true"])

    logger.info(f"🚀 Launching Web Application on http://{address}:{port}")
    logger.info("   Press Ctrl+C to stop the application gracefully.\n")

    try:
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down application...")
    finally:
        if scheduler.is_running():
            logger.info("🧹 Stopping background scheduler...")
            scheduler.stop()


def main():
    parser = argparse.ArgumentParser(
        prog="launcher",
        description="Albion Market Strategist Pro — Orchestration Launcher",
    )
    parser.add_argument("--server", action="store_true", help="Run in server mode (headless/VPS deployment)")
    parser.add_argument("--address", default=settings.streamlit_address, help="Bind address for Web UI")
    parser.add_argument("--port", type=int, default=settings.streamlit_port, help="Port for Web UI")
    parser.add_argument("--check", action="store_true", help="Run self-diagnostics check and exit")
    parser.add_argument("--worker-only", action="store_true", help="Run background price collector only")

    args = parser.parse_args()

    if args.check:
        run_check()
        sys.exit(0)

    if args.worker_only:
        print_banner()
        hc = SystemHealthCheck()
        hc.self_heal()
        from src.workers.price_collector import PriceCollectorWorker
        worker = PriceCollectorWorker(db_path=settings.db_path, interval_seconds=settings.scheduler_interval)
        worker.start()
        sys.exit(0)

    # Default / UI mode
    launch_server(address=args.address, port=args.port, is_headless=args.server)


if __name__ == "__main__":
    main()
