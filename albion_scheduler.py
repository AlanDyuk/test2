#!/usr/bin/env python3
"""
Scheduler — cross-platform background process manager.
Replaces the old Windows-specific subprocess approach.
"""
from __future__ import annotations

import argparse
import sys

from services.scheduler import Scheduler
from collectors.base import MarketPricesCollector


def start(interval: int = 300, db_path: str = None):
    """Start the scheduler."""
    from config.settings import settings

    db = db_path or settings.db_path
    scheduler = Scheduler()

    print(f"[+] Scheduler started. Interval: {interval}s")
    print(f"    PID file: {scheduler.pid_file}")

    scheduler.start(interval=interval, collector_script="albion_data_collector.py")

    # Keep main thread alive
    try:
        while scheduler.is_running():
            import time
            time.sleep(5)
    except KeyboardInterrupt:
        print("\n[+] Stopping scheduler...")
        scheduler.stop()


def stop():
    """Stop the scheduler."""
    scheduler = Scheduler()
    if scheduler.stop():
        print("[+] Scheduler stopped")
    else:
        print("[!] Scheduler not running or PID file missing")


def status():
    """Show scheduler status."""
    scheduler = Scheduler()
    if scheduler.is_running():
        print("🟢 Scheduler is running")
    else:
        print("⚪ Scheduler is stopped")
        scheduler.cleanup_stale_pid()


def main():
    parser = argparse.ArgumentParser(description="Price collection scheduler")
    subparsers = parser.add_subparsers(dest="command")

    start_p = subparsers.add_parser("start", help="Start scheduler")
    start_p.add_argument("--interval", type=int, default=300, help="Interval (seconds)")
    start_p.add_argument("--db", help="Database path")

    stop_p = subparsers.add_parser("stop", help="Stop scheduler")
    status_p = subparsers.add_parser("status", help="Show scheduler status")

    args = parser.parse_args()

    if args.command == "start":
        start(interval=args.interval, db_path=args.db)
    elif args.command == "stop":
        stop()
    elif args.command == "status":
        status()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
