"""Trade analysis service — calculates arbitrage opportunities with independent buy/sell freshness."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def analyze_trades(
    conn: sqlite3.Connection,
    tracked_items: Optional[List[str]] = None,
    target_cities: Optional[List[str]] = None,
    has_premium: bool = True,
    max_hours_old: int = 6,
    trade_mode: str = "order_flip",
    sales_tax_rate: float = 0.040,
    setup_fee_rate: float = 0.025,
) -> List[Dict[str, Any]]:
    """
    Analyze trade opportunities between cities with independent buy/sell timestamps.

    Args:
        conn: Database connection
        tracked_items: Items to analyze (None = all)
        target_cities: Cities to consider (None = all)
        has_premium: Whether user has premium account
        max_hours_old: Max age in hours for both buy and sell prices
        trade_mode: "order_flip" or "instant"
        sales_tax_rate: Tax for sales (4% premium / 8% standard)
        setup_fee_rate: Setup fee for order placement (2.5%)
    """
    if trade_mode == "instant":
        total_tax_rate = sales_tax_rate
    else:
        total_tax_rate = setup_fee_rate + sales_tax_rate

    cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=max_hours_old)
                   ).strftime("%Y-%m-%dT%H:%M:%S")

    where_conditions = [
        "(m.sell_price_min > 0 OR m.buy_price_max > 0)"
    ]
    params: List[Any] = []

    # Filter by tracked items
    if tracked_items:
        placeholders = ",".join(["?"] * len(tracked_items))
        where_conditions.append(f"m.item_unique_name IN ({placeholders})")
        params.extend(tracked_items)

    # Filter by cities
    if target_cities:
        placeholders = ",".join(["?"] * len(target_cities))
        where_conditions.append(f"m.city_name IN ({placeholders})")
        params.extend(target_cities)

    where_clause = " AND ".join(where_conditions)

    query = f"""
        SELECT
            m.item_unique_name,
            m.city_name,
            m.quality,
            m.sell_price_min,
            m.buy_price_max,
            m.timestamp,
            m.sell_updated_at,
            m.buy_updated_at,
            i.ru_name,
            i.en_name
        FROM market_prices m
        LEFT JOIN items i ON m.item_unique_name = i.unique_name
        WHERE {where_clause}
    """

    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()

    now_dt = datetime.now(timezone.utc).replace(tzinfo=None)

    # Build price matrix per city with independent timestamps
    prices: Dict[tuple, Dict[str, Any]] = {}
    for row in rows:
        item_id = row[0]
        city = row[1]
        quality = row[2]
        sell_min = row[3]
        buy_max = row[4]
        sell_ts = row[6] or row[5]
        buy_ts = row[7] or row[5]
        ru_name = row[8]
        en_name = row[9]

        key = (item_id, quality, city)

        s_price = sell_min if (sell_min is not None and sell_min > 0) else None
        b_price = buy_max if (buy_max is not None and buy_max > 0) else None

        # Parse independent timestamp ages
        sell_age_mins = 99999
        buy_age_mins = 99999

        if sell_ts:
            try:
                dt = datetime.strptime(str(sell_ts)[:19], "%Y-%m-%dT%H:%M:%S")
                sell_age_mins = max(0, int((now_dt - dt).total_seconds() / 60))
            except ValueError:
                pass

        if buy_ts:
            try:
                dt = datetime.strptime(str(buy_ts)[:19], "%Y-%m-%dT%H:%M:%S")
                buy_age_mins = max(0, int((now_dt - dt).total_seconds() / 60))
            except ValueError:
                pass

        if s_price is not None or b_price is not None:
            prices[key] = {
                "sell_min": s_price,
                "buy_max": b_price,
                "sell_age_mins": sell_age_mins,
                "buy_age_mins": buy_age_mins,
                "ru_name": ru_name,
                "en_name": en_name,
            }

    # Find trade opportunities
    trade_opportunities: List[Dict[str, Any]] = []

    # Get distinct (item, quality)
    item_qualities = set((k[0], k[1]) for k in prices.keys())
    max_mins = max_hours_old * 60

    for item, quality in item_qualities:
        # Collect prices across cities for this item/quality
        city_prices = {}
        for (i, q, city), data in prices.items():
            if i == item and q == quality:
                city_prices[city] = data

        cities_list = list(city_prices.keys())

        for i_buy, buy_city in enumerate(cities_list):
            for i_sell, sell_city in enumerate(cities_list):
                if buy_city == sell_city:
                    continue

                buy_info = city_prices[buy_city]
                sell_info = city_prices[sell_city]

                # We buy in buy_city from cheapest sell order
                buy_price = buy_info.get("sell_min")
                buy_age = buy_info.get("sell_age_mins", 99999)

                if not buy_price or buy_price <= 0 or buy_age > max_mins:
                    continue  # Buy price missing or stale

                # We sell in sell_city:
                # If mode == "instant", we sell to buy_price_max (freshness: buy_age_mins)
                # If mode == "order_flip", we list sell order at sell_price_min (freshness: sell_age_mins)
                if trade_mode == "instant":
                    sell_price = sell_info.get("buy_max")
                    sell_age = sell_info.get("buy_age_mins", 99999)
                else:
                    sell_price = sell_info.get("sell_min")
                    sell_age = sell_info.get("sell_age_mins", 99999)

                if not sell_price or sell_price <= 0 or sell_age > max_mins:
                    continue  # Sell price missing or stale

                if sell_price <= buy_price:
                    continue  # No profit before tax

                gross_profit = sell_price - buy_price
                net_sell = sell_price * (1.0 - total_tax_rate)
                net_profit = net_sell - buy_price

                if net_profit <= 0:
                    continue  # No profit after tax

                item_label = buy_info.get("ru_name") or buy_info.get("en_name") or item

                trade_opportunities.append({
                    "item": item,
                    "item_name": item_label,
                    "quality": quality,
                    "buy_city": buy_city,
                    "buy_price": buy_price,
                    "buy_age_mins": buy_age,
                    "sell_city": sell_city,
                    "sell_price": sell_price,
                    "sell_age_mins": sell_age,
                    "gross_profit": gross_profit,
                    "net_profit": net_profit,
                    "profit_percentage": (net_profit / buy_price * 100) if buy_price > 0 else 0,
                    "tax_rate": total_tax_rate * 100,
                    "is_premium": has_premium,
                    "trade_mode": trade_mode,
                    "age_minutes": max(buy_age, sell_age),
                    "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
                })

    # Sort by net profit descending
    trade_opportunities.sort(key=lambda x: x["net_profit"], reverse=True)

    return trade_opportunities


def get_trade_opportunities(
    db_path: str = "albion_market.db",
    tracked_items: Optional[List[str]] = None,
    target_cities: Optional[List[str]] = None,
    has_premium: bool = True,
    max_hours_old: int = 6,
    trade_mode: str = "order_flip",
) -> List[Dict[str, Any]]:
    """
    Convenience wrapper — connects to DB and runs analysis.
    """
    import sqlite3
    try:
        from src.config.settings import settings
    except ImportError:
        from albion_strategist_refactor.config.settings import settings

    conn = sqlite3.connect(db_path)
    try:
        return analyze_trades(
            conn=conn,
            tracked_items=tracked_items or settings.filtered_items,
            target_cities=target_cities,
            has_premium=has_premium,
            max_hours_old=max_hours_old,
            trade_mode=trade_mode,
            sales_tax_rate=settings.sales_tax_premium if has_premium
                else settings.sales_tax_standard,
        )
    finally:
        conn.close()
