"""CLI entry point for Albion Market Strategist."""
from __future__ import annotations

import argparse
import logging
import os
import sys
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


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def main():
    parser = argparse.ArgumentParser(
        prog="albion",
        description="Albion Market Strategist Pro - CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- sync command ---
    sync_parser = subparsers.add_parser("sync", help="Sync item catalog to database")
    sync_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    # --- analyze command ---
    analyze_parser = subparsers.add_parser("analyze", help="Run trade analysis")
    analyze_parser.add_argument("--hours", "-t", type=int, default=6,
                                help="Hours of price freshness (default: 6)")
    analyze_parser.add_argument("--premium", action="store_true", default=True,
                                help="Use premium tax rates")
    analyze_parser.add_argument("--mode", choices=["order_flip", "instant"],
                                default="order_flip", help="Trade mode")
    analyze_parser.add_argument("--output", "-o", help="Output file (JSON)")
    analyze_parser.add_argument("--verbose", "-v", action="store_true")

    # --- collect command ---
    collect_parser = subparsers.add_parser("collect", help="Collect market prices")
    collect_parser.add_argument("--interval", type=int, default=300,
                                help="Interval in seconds")
    collect_parser.add_argument("--verbose", "-v", action="store_true")

    # --- serve command ---
    serve_parser = subparsers.add_parser("serve", help="Start Streamlit web app")
    serve_parser.add_argument("--port", type=int, default=8501, help="Port")
    serve_parser.add_argument("--address", default="0.0.0.0", help="Bind address")
    serve_parser.add_argument("--verbose", "-v", action="store_true")

    # --- cat command ---
    cat_parser = subparsers.add_parser("cat", help="List item catalog")
    cat_parser.add_argument("--category", "-c", help="Show only this category")
    cat_parser.add_argument("--tier", "-t", help="Filter by tier (3-8)")
    cat_parser.add_argument("--ench", "-e", help="Filter by enchantment (.0-.4)")

    # --- filter command ---
    filter_parser = subparsers.add_parser("filter", help="Filter resources")
    filter_parser.add_argument("--output", "-o", help="Output file (default: filtered_resource_items.json)")

    # --- password command ---
    pw_parser = subparsers.add_parser("password", help="Set/change app password")
    pw_parser.add_argument("--hash", help="Set pre-hashed password")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    setup_logging(getattr(args, "verbose", False))

    if args.command == "sync":
        _cmd_sync()
    elif args.command == "analyze":
        _cmd_analyze(args)
    elif args.command == "collect":
        _cmd_collect(args)
    elif args.command == "serve":
        _cmd_serve(args)
    elif args.command == "cat":
        _cmd_cat(args)
    elif args.command == "filter":
        _cmd_filter(args)
    elif args.command == "password":
        _cmd_password(args)


def _cmd_sync():
    """Sync item catalog."""
    from src.db.engine import DatabaseEngine
    from src.collectors.base import CatalogSyncCollector

    from src.config.settings import settings
    engine = DatabaseEngine(settings.db_path)

    with engine.session() as conn:
        collector = CatalogSyncCollector(
            db_path=settings.db_path,
            items_json_file=settings.items_json_file,
            world_json_file=settings.world_json_file,
        )
        collector.collect(conn)

    engine.close()
    logger.info("✅ Catalog sync complete")


def _cmd_analyze(args):
    """Run trade analysis."""
    from src.services.trade_analyzer import get_trade_opportunities
    from src.config.settings import settings
    import json

    # Load tracked items
    tracked = settings.filtered_items if settings.filtered_items else []
    if not tracked:
        logger.warning("No tracked items found. Run 'albion filter' first.")
        sys.exit(1)

    # Load target cities
    cities = [c.name for c in settings.available_cities]

    opportunities = get_trade_opportunities(
        db_path=settings.db_path,
        tracked_items=tracked,
        target_cities=cities,
        has_premium=args.premium,
        max_hours_old=args.hours,
        trade_mode=args.mode,
    )

    print(f"\nFound {len(opportunities)} trade opportunities\n")
    print(f"{'Item':<40} {'Buy':<12} {'Sell':<12} {'Profit':<10} {'Margin':<8}")
    print("-" * 85)

    for trade in opportunities[:30]:
        name = trade.get("item_name", trade["item"])[:38]
        print(f"{name:<40} {trade['buy_city']:<12} {trade['sell_city']:<12}"
              f" +{trade['net_profit']:>8,.0f}  {trade['profit_percentage']:>7.1f}%")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(opportunities, f, ensure_ascii=False, indent=2)
        logger.info(f"Results saved to {args.output}")


def _cmd_collect(args):
    """Run price collection."""
    from src.collectors.base import MarketPricesCollector
    from src.config.settings import settings
    from src.db.engine import DatabaseEngine

    engine = DatabaseEngine(settings.db_path)

    with engine.session() as conn:
        collector = MarketPricesCollector(db_path=settings.db_path)
        collector.collect(conn)

    engine.close()
    logger.info("✅ Collection complete")


def _cmd_serve(args):
    """Start Streamlit app."""
    os.environ["STREAMLIT_SERVER_PORT"] = str(args.port)
    os.environ["STREAMLIT_SERVER_ADDRESS"] = args.address

    import subprocess
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        "src/ui/streamlit/main.py",
        "--server.port", str(args.port),
        "--server.address", args.address,
    ]
    logger.info(f"Starting Streamlit on {args.address}:{args.port}")
    subprocess.run(cmd)


def _cmd_cat(args):
    """List item catalog."""
    from src.services.item_categorizer import get_categorized_items

    catalog = get_categorized_items()

    if args.category:
        # Show specific category
        for main_cat, subs in catalog.items():
            if args.category in main_cat or args.category.lower() in main_cat.lower():
                print(f"\n{main_cat}:")
                for sub, items in subs.items():
                    print(f"  {sub}: {len(items)} items")
    else:
        for main_cat, subs in catalog.items():
            total = sum(len(items) for items in subs.values())
            print(f"{main_cat}: {total} items")
            if args.tier or args.ench:
                for sub, items in subs.items():
                    print(f"  {sub}: {len(items)} items")


def _cmd_filter(args):
    """Filter resources."""
    from src.services.item_categorizer import filter_resource_items, save_filtered_items

    output = args.output or "filtered_resource_items.json"
    items = filter_resource_items()
    save_filtered_items(items, output)


def _cmd_password(args):
    """Set password."""
    from src.auth.password_manager import PasswordManager

    pm = PasswordManager()
    if args.hash:
        # Write hash to .env
        Path(".env").write_text(f"APP_PASSWORD={args.hash}\n", encoding="utf-8")
        logger.info("Password hash set in .env")
    else:
        # Read from .env and hash it
        hashed = pm.check_password_file()
        if hashed:
            logger.info(f"Password hashed and stored in .env")
        else:
            logger.info("No password set. Edit .env and add APP_PASSWORD=<your_password>")
            logger.info("Then run again to auto-hash it.")


if __name__ == "__main__":
    main()
