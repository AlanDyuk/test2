#!/usr/bin/env python3
"""
Filter items — filters resources for tracking.
Updated to use the modular architecture.
"""
from __future__ import annotations

import argparse

from services.item_categorizer import filter_resource_items, save_filtered_items


def main():
    parser = argparse.ArgumentParser(description="Filter resource items for tracking")
    parser.add_argument("--output", "-o",
                        default="filtered_resource_items.json",
                        help="Output file path")
    args = parser.parse_args()

    items = filter_resource_items()

    print(f"[+] Отфильтровано {len(items)} ресурсов (T3-T7, @0-3)")

    # Save
    save_filtered_items(items, args.output)

    # Show first 20
    print(f"\n--- Первые 20 --- ")
    for i, item in enumerate(items[:20]):
        print(f"  {i+1}. {item}")


if __name__ == "__main__":
    main()
