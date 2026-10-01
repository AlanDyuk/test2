"""Item categorizer service — categorizes items into auction categories."""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional


def get_categorized_items(items_path: str = "items.json") -> Dict[str, Dict[str, List[str]]]:
    """
    Return a hierarchical catalog of Albion Online items.
    Structure: {main_category: {sub_category: [item_ids]}}
    """
    catalog: Dict[str, Dict[str, List[str]]] = {
        "🪵 Ресурсы": {
            "Дерево (Wood)": [],
            "Руда (Ore)": [],
            "Волокно (Fiber)": [],
            "Шкуры (Hide)": [],
            "Камень (Rock)": [],
            "Рыба (Fish)": [],
        },
        "🛠️ Инструменты": {
            "Собирательные Инструменты": [],
        },
        "🧪 Расходники": {
            "Еда (Food)": [],
            "Зелья (Potions)": [],
        },
        "🎒 Аксессуары & Маунты": {
            "Сумки (Bags)": [],
            "Обычные Плащи": [],
            "Фракционные Плащи": [],
            "Ездовые животные (Mounts)": [],
        },
        "🛡️ Доспехи и Броня": {
            "🧵 Тканевая Броня (Cloth/Robe)": [],
            "🥋 Кожаная Броня (Leather)": [],
            "🛡️ Тяжелая Латная Броня (Plate)": [],
        },
        "⚔️ Ветви Оружия": {
            "⚔️ Мечи (Swords)": [],
            "🪓 Топоры (Axes)": [],
            "🔨 Булавы и Молоты (Maces & Hammers)": [],
            "🗡️ Кинжалы и Копья (Daggers & Spears)": [],
            "🏹 Луки и Арбалеты (Bows & Crossbows)": [],
            "🔥 Огненные Посохи (Fire Staves)": [],
            "❄️ Ледяные Посохи (Frost Staves)": [],
            "🌿 Природная и Священная Магия (Nature & Holy)": [],
            "🔮 Чародейские и Проклятые Посохи (Arcane & Cursed)": [],
            "🥊 Кастеты и Древоделы (Quarterstaves & Knuckles)": [],
            "🛡️ Левая рука (Shields/Offhand/Tomes)": [],
        },
    }

    if not os.path.exists(items_path):
        return catalog

    try:
        with open(items_path, "r", encoding="utf-8") as f:
            items_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        return catalog

    junk_patterns = ["FURNITURE", "SKIN_", "TOKEN", "QUEST", "NONTRADABLE",
                     "LOOTBAG", "ARENA", "DUMMY", "VANITY"]

    for entry in items_data:
        unique_name = entry.get("UniqueName", "").strip()
        if not unique_name:
            continue

        # Skip non-tradable items
        if any(junk in unique_name for junk in junk_patterns):
            continue

        # Tools
        if any(tool in unique_name for tool in [
            "PICKAXE", "SICKLE", "SKINNINGKNIFE", "WOODAXE",
            "DEMOLITIONHAMMER", "FISHINGROD"
        ]):
            if re.match(r"^T[2-8]_TOOL_", unique_name) or "TOOL" in unique_name:
                catalog["🛠️ Инструменты"]["Собирательные Инструменты"].append(unique_name)
                continue

        # Resources
        if re.match(r"^T[1-8]_WOOD", unique_name):
            catalog["🪵 Ресурсы"]["Дерево (Wood)"].append(unique_name)
        elif re.match(r"^T[1-8]_ORE", unique_name):
            catalog["🪵 Ресурсы"]["Руда (Ore)"].append(unique_name)
        elif re.match(r"^T[1-8]_FIBER", unique_name):
            catalog["🪵 Ресурсы"]["Волокно (Fiber)"].append(unique_name)
        elif re.match(r"^T[1-8]_HIDE", unique_name):
            catalog["🪵 Ресурсы"]["Шкуры (Hide)"].append(unique_name)
        elif re.match(r"^T[1-8]_ROCK", unique_name):
            catalog["🪵 Ресурсы"]["Камень (Rock)"].append(unique_name)
        elif re.match(r"^T[1-8]_FISH", unique_name) or unique_name.startswith("FISH_"):
            catalog["🪵 Ресурсы"]["Рыба (Fish)"].append(unique_name)
        # Clothing
        elif re.search(r"(ROBE|CLOTH|LEATHER|PLATE|HELM|CHEST|GLOVES|BOOTS|BELT|SHOULDER)", unique_name, re.I):
            if "CLOTH" in unique_name or "ROBE" in unique_name:
                catalog["🛡️ Доспехи и Броня"]["🧵 Тканевая Броня (Cloth/Robe)"].append(unique_name)
            elif "LEATHER" in unique_name:
                catalog["🛡️ Доспехи и Броня"]["🥋 Кожаная Броня (Leather)"].append(unique_name)
            elif "PLATE" in unique_name:
                catalog["🛡️ Доспехи и Броня"]["🛡️ Тяжелая Латная Броня (Plate)"].append(unique_name)
            else:
                catalog["🛡️ Доспехи и Броня"]["🛡️ Тяжелая Латная Броня (Plate)"].append(unique_name)
        # Weapons
        elif re.search(r"(SWORD|AXE|MACE|HAMMER|DAGGER|SPEAR|BOW|CROSSBOW|FIRE_STAFF|FROST_STAFF|NATURE_STAFF|HOLY_STAFF|ARCANE_STAFF|CURSED_STAFF|KNUCKLES|KNIFE)", unique_name, re.I):
            if "SWORD" in unique_name:
                catalog["⚔️ Ветви Оружия"]["⚔️ Мечи (Swords)"].append(unique_name)
            elif "AXE" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🪓 Топоры (Axes)"].append(unique_name)
            elif "MACE" in unique_name or "HAMMER" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🔨 Булавы и Молоты (Maces & Hammers)"].append(unique_name)
            elif "DAGGER" in unique_name or "SPEAR" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🗡️ Кинжалы и Копья (Daggers & Spears)"].append(unique_name)
            elif "BOW" in unique_name or "CROSSBOW" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🏹 Луки и Арбалеты (Bows & Crossbows)"].append(unique_name)
            elif "FIRE_STAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🔥 Огненные Посохи (Fire Staves)"].append(unique_name)
            elif "FROST_STAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["❄️ Ледяные Посохи (Frost Staves)"].append(unique_name)
            elif "NATURE_STAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🌿 Природная и Священная Магия (Nature & Holy)"].append(unique_name)
            elif "HOLY_STAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🌿 Природная и Священная Магия (Nature & Holy)"].append(unique_name)
            elif "ARCANE_STAFF" in unique_name or "CURSED_STAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🔮 Чародейские и Проклятые Посохи (Arcane & Cursed)"].append(unique_name)
            elif "KNUCKLES" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🥊 Кастеты и Древоделы (Quarterstaves & Knuckles)"].append(unique_name)
        # Bags
        elif "BAG" in unique_name.upper():
            catalog["🎒 Аксессуары & Маунты"]["Сумки (Bags)"].append(unique_name)
        # Cloaks
        elif "CLOAK" in unique_name.upper():
            if "FACTION" in unique_name.upper():
                catalog["🎒 Аксессуары & Маунты"]["Фракционные Плащи"].append(unique_name)
            else:
                catalog["🎒 Аксессуары & Маунты"]["Обычные Плащи"].append(unique_name)
        # Mounts
        elif "MOUNT" in unique_name.upper():
            catalog["🎒 Аксессуары & Маунты"]["Ездовые животные (Mounts)"].append(unique_name)
        # Food
        elif "MEAL" in unique_name.upper() or "POTION" in unique_name.upper():
            if "MEAL" in unique_name.upper():
                catalog["🧪 Расходники"]["Еда (Food)"].append(unique_name)
            else:
                catalog["🧪 Расходники"]["Зелья (Potions)"].append(unique_name)

    return catalog


def filter_resource_items(items_path: str = "items.json") -> List[str]:
    """
    Filter items to only trackable resources (T3-T7, @0-3).
    Returns sorted list of UniqueNames.
    """
    if not os.path.exists(items_path):
        return []

    with open(items_path, "r", encoding="utf-8") as f:
        items_data = json.load(f)

    pattern = re.compile(r"^T([3-7])_((WOOD|ORE|FIBER|HIDE|ROCK)|FISH)")
    filtered = []

    for entry in items_data:
        unique_name = entry.get("UniqueName", "")
        if not unique_name:
            continue

        match = pattern.match(unique_name)
        if not match:
            # FISH items without T prefix
            if unique_name.startswith("FISH_") or unique_name == "FISH":
                if not re.match(r"^T([3-7])_FISH", unique_name):
                    continue
            else:
                continue

        tier_str = match.group(1)
        try:
            tier = int(tier_str)
        except ValueError:
            continue

        if not (3 <= tier <= 7):
            continue

        # Check enchantment level
        enchant_match = re.search(r"@(\d)", unique_name)
        if enchant_match:
            enchant = int(enchant_match.group(1))
            if not (0 <= enchant <= 3):
                continue

        filtered.append(unique_name)

    return sorted(list(set(filtered)))


def save_filtered_items(items: List[str], output_path: str = "filtered_resource_items.json"):
    """Save filtered resources to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2)
    print(f"[+] Saved {len(items)} filtered resources to {output_path}")


if __name__ == "__main__":
    items = filter_resource_items()
    print(f"[+] Filtered {len(items)} resources")
    save_filtered_items(items)
    for i, item in enumerate(items[:20]):
        print(f"  {i+1}. {item}")
