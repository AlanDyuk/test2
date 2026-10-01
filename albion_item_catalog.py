import json
import os
import re

ITEMS_JSON = "items.json"

def get_categorized_items():
    catalog = {
        "🪵 Ресурсы": {
            "Дерево (Wood)": [],
            "Руда (Ore)": [],
            "Волокно (Fiber)": [],
            "Шкуры (Hide)": [],
            "Камень (Rock)": [],
            "Рыба (Fish)": []
        },
        "🛠️ Инструменты": {
            "Собирательные Инструменты": []
        },
        "🧪 Расходники": {
            "Еда (Food)": [],
            "Зелья (Potions)": []
        },
        "🎒 Аксессуары & Маунты": {
            "Сумки (Bags)": [],
            "Обычные Плащи": [],
            "Фракционные Плащи": [],
            "Ездовые животные (Mounts)": []
        },
        "🛡️ Доспехи и Броня": {
            "🧵 Тканевая Броня (Cloth/Robe)": [],
            "🥋 Кожаная Броня (Leather)": [],
            "🛡️ Тяжелая Латная Броня (Plate)": []
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
            "🛡️ Левая рука (Shields/Offhand/Tomes)": []
        }
    }

    if not os.path.exists(ITEMS_JSON):
        return catalog

    try:
        with open(ITEMS_JSON, "r", encoding="utf-8") as f:
            items_data = json.load(f)

        for entry in items_data:
            unique_name = entry.get("UniqueName", "").strip()
            if not unique_name:
                continue

            if any(junk in unique_name for junk in ["FURNITURE", "SKIN_", "TOKEN", "QUEST", "NONTRADABLE", "LOOTBAG", "ARENA", "DUMMY", "VANITY"]):
                continue

            # 1. ИНСТРУМЕНТЫ (TOOLS)
            if any(tool in unique_name for tool in ["PICKAXE", "SICKLE", "SKINNINGKNIFE", "WOODAXE", "DEMOLITIONHAMMER", "FISHINGROD"]):
                if re.match(r"^T[2-8]_TOOL_", unique_name) or "TOOL" in unique_name:
                    catalog["🛠️ Инструменты"]["Собирательные Инструменты"].append(unique_name)
                    continue

            # 2. РЕСУРСЫ
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
            elif re.match(r"^T[1-8]_FISH", unique_name) or unique_name.startswith("T1_FISH"):
                catalog["🪵 Ресурсы"]["Рыба (Fish)"].append(unique_name)

            # 3. РАСХОДНИКИ
            elif "MEAL_" in unique_name or "FOOD_" in unique_name:
                catalog["🧪 Расходники"]["Еда (Food)"].append(unique_name)
            elif "POTION_" in unique_name:
                catalog["🧪 Расходники"]["Зелья (Potions)"].append(unique_name)

            # 4. АКСЕССУАРЫ И МАУНТЫ
            elif "BAG" in unique_name and "CAPE" not in unique_name:
                catalog["🎒 Аксессуары & Маунты"]["Сумки (Bags)"].append(unique_name)
            elif "CAPEITEM" in unique_name and "BAG" not in unique_name:
                catalog["🎒 Аксессуары & Маунты"]["Фракционные Плащи"].append(unique_name)
            elif "_CAPE" in unique_name and "BAG" not in unique_name and "CAPEITEM" not in unique_name:
                catalog["🎒 Аксессуары & Маунты"]["Обычные Плащи"].append(unique_name)
            elif re.match(r"^T[2-8]_(MOUNT|HORSE|OX|SWIFTCLAW|DIREWOLF|DIREBEAR)", unique_name):
                catalog["🎒 Аксессуары & Маунты"]["Ездовые животные (Mounts)"].append(unique_name)

            # 5. ДОСПЕХИ И БРОНЯ
            elif "_CLOTH" in unique_name:
                if re.match(r"^T[3-8]_", unique_name):
                    catalog["🛡️ Доспехи и Броня"]["🧵 Тканевая Броня (Cloth/Robe)"].append(unique_name)
            elif "_LEATHER" in unique_name:
                if re.match(r"^T[3-8]_", unique_name):
                    catalog["🛡️ Доспехи и Броня"]["🥋 Кожаная Броня (Leather)"].append(unique_name)
            elif "_PLATE" in unique_name:
                if re.match(r"^T[3-8]_", unique_name):
                    catalog["🛡️ Доспехи и Броня"]["🛡️ Тяжелая Латная Броня (Plate)"].append(unique_name)

            # 6. ОРУЖИЕ ПО ВЕТВЯМ
            elif any(w in unique_name for w in ["SWORD", "CLEAVER", "DUALSWORD", "CLAYMORE"]):
                catalog["⚔️ Ветви Оружия"]["⚔️ Мечи (Swords)"].append(unique_name)
            elif "AXE" in unique_name or "HALBERD" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🪓 Топоры (Axes)"].append(unique_name)
            elif any(w in unique_name for w in ["MACE", "HAMMER", "RAM"]):
                catalog["⚔️ Ветви Оружия"]["🔨 Булавы и Молоты (Maces & Hammers)"].append(unique_name)
            elif any(w in unique_name for w in ["DAGGER", "SPEAR", "PIKE"]):
                catalog["⚔️ Ветви Оружия"]["🗡️ Кинжалы и Копья (Daggers & Spears)"].append(unique_name)
            elif "BOW" in unique_name or "CROSSBOW" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🏹 Луки и Арбалеты (Bows & Crossbows)"].append(unique_name)
            elif "FIRESTAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🔥 Огненные Посохи (Fire Staves)"].append(unique_name)
            elif "FROSTSTAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["❄️ Ледяные Посохи (Frost Staves)"].append(unique_name)
            elif "HOLYSTAFF" in unique_name or "NATURESTAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🌿 Природная и Священная Магия (Nature & Holy)"].append(unique_name)
            elif "ARCANESTAFF" in unique_name or "CURSEDSTAFF" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🔮 Чародейские и Проклятые Посохи (Arcane & Cursed)"].append(unique_name)
            elif "QUARTERSTAFF" in unique_name or "KNUCKLES" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🥊 Кастеты и Древоделы (Quarterstaves & Knuckles)"].append(unique_name)
            elif "_OFF_" in unique_name or "SHIELD" in unique_name or "TOME" in unique_name or "TORCH" in unique_name or "ORB" in unique_name:
                catalog["⚔️ Ветви Оружия"]["🛡️ Левая рука (Shields/Offhand/Tomes)"].append(unique_name)

    except Exception as e:
        print(f"[!] Ошибка разбора каталога: {e}")

    for main_cat in catalog:
        for sub_cat in catalog[main_cat]:
            catalog[main_cat][sub_cat] = sorted(list(set(catalog[main_cat][sub_cat])))

    return catalog
