#!/usr/bin/env python3
"""
Trade analyzer — standalone entry point.
Kept for backwards compatibility and CLI usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Automatically discover and attach project root to sys.path
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from src.config.settings import settings
from src.services.trade_analyzer import get_trade_opportunities

# Backward compatibility alias for legacy albion_streamlit_app.py
analyze_trades = get_trade_opportunities


def analyze(
    db_path: str = None,
    has_premium: bool = True,
    max_hours: int = 6,
    trade_mode: str = "order_flip",
    output_file: str = None,
):
    """Run trade analysis and print/save results."""
    path = db_path or settings.db_path

    # Load tracked items
    import os
    tracked_items = []
    if os.path.exists(settings.filtered_items_file):
        with open(settings.filtered_items_file, "r", encoding="utf-8") as f:
            tracked_items = json.load(f)

    if not tracked_items:
        print("[!] No tracked items. Run filter_items.py first.")
        sys.exit(1)

    # Load target cities
    target_cities = [c.name for c in settings.available_cities]
    if os.path.exists(settings.target_cities_file):
        with open(settings.target_cities_file, "r", encoding="utf-8") as f:
            target_cities = json.load(f) or target_cities

    # Run analysis
    opportunities = get_trade_opportunities(
        db_path=path,
        tracked_items=tracked_items,
        target_cities=target_cities,
        has_premium=has_premium,
        max_hours_old=max_hours,
        trade_mode=trade_mode,
    )

    # Print results
    print(f"\n{'='*85}")
    print(f"Найдено выгодных связок: {len(opportunities)}")
    print(f"Режим: {trade_mode} | Премиум: {has_premium} | Окно: {max_hours}ч")
    print(f"{'='*85}")
    print(f"{'Предмет':<40} {'Покупка':<12} {'Продажа':<12} {'Прибыль':<10} {'Маржа':<8}")
    print("-"*85)

    for trade in opportunities[:50]:
        name = trade.get("item_name", trade["item"])[:38]
        print(f"{name:<40} {trade['buy_city']:<12} {trade['sell_city']:<12}"
              f" +{trade['net_profit']:>8,.0f}  {trade['profit_percentage']:>7.1f}%")

    # Save to file
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(opportunities, f, ensure_ascii=False, indent=2)
        print(f"\n[+] Results saved to {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Analyze trade opportunities")
    parser.add_argument("--premium", action="store_true", default=True,
                        help="Use premium tax rates")
    parser.add_argument("--no-premium", action="store_true",
                        help="Use standard tax rates")
    parser.add_argument("--hours", "-t", type=int, default=6,
                        help="Price freshness window (hours)")
    parser.add_argument("--mode", "-m", choices=["order_flip", "instant"],
                        default="order_flip", help="Trade mode")
    parser.add_argument("--output", "-o", help="Output JSON file")
    args = parser.parse_args()

    if args.no_premium:
        args.premium = False

    analyze(
        has_premium=args.premium,
        max_hours=args.hours,
        trade_mode=args.mode,
        output_file=args.output,
    )


if __name__ == "__main__":
    main()
