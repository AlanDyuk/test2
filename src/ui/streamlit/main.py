"""Streamlit main application entry point."""
from __future__ import annotations

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

from src.config.settings import settings
from src.auth.password_manager import PasswordManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("streamlit_app")

# Initialize password manager
pwd_manager = PasswordManager()

# Set up hashed password from .env if set
if not settings.hashed_password:
    hashed = pwd_manager.check_password_file()
    if hashed:
        logger.info("Password loaded from .env")


# --- Streamlit Imports (lazy to avoid startup overhead) ---
import streamlit as st
import pandas as pd

# Page config
st.set_page_config(
    layout="wide",
    page_title=settings.app_name,
    page_icon="⚔️",
)


def check_password() -> bool:
    """Verify password authentication with robust st.form handling."""
    if st.session_state.get("password_correct", False):
        return True

    st.title("⚔️ Albion Market Strategist Pro")
    st.subheader("🔒 Доступ ограничен. Введите пароль для входа:")

    with st.form("login_form", clear_on_submit=False):
        password_input = st.text_input("Пароль доступа", type="password", key="password_input")
        submit_button = st.form_submit_button("Войти")

        if submit_button:
            if pwd_manager.verify(password_input.strip(), settings.hashed_password):
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("❌ Неверный пароль. Попробуйте еще раз.")

    return False


if not check_password():
    st.stop()


# --- Custom CSS Styling ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    div[data-testid="stDecoration"] {display:none;}
    .stApp {
        background-color: #12141d;
        color: #e0e6ed;
    }
    .buy-badge {
        background-color: #1b382b;
        color: #4ade80;
        padding: 3px 8px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .sell-badge {
        background-color: #1c2d42;
        color: #60a5fa;
        padding: 3px 8px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 0.9em;
    }
    .profit-badge {
        background-color: #3b2d14;
        color: #facc15;
        padding: 4px 10px;
        border-radius: 5px;
        font-weight: bold;
        font-size: 1.1em;
    }
    </style>
""", unsafe_allow_html=True)


CITY_BADGES = {
    "Fort Sterling": "🏰 Fort Sterling",
    "Lymhurst": "🌲 Lymhurst",
    "Bridgewatch": "🏜️ Bridgewatch",
    "Martlock": "🌾 Martlock",
    "Thetford": "🐸 Thetford",
    "Caerleon": "💀 Caerleon",
    "Brecilien": "🌀 Brecilien"
}


def get_item_icon_url(item_unique_name: str) -> str:
    """Return render icon URL for Albion item."""
    clean_id = item_unique_name.strip()
    return f"https://render.albiononline.com/v1/item/{clean_id}.png"


def render_city_selector():
    """Render top city filter badges."""
    st.markdown("### 🌆 Фильтр Городов Торговли")

    if "target_cities" not in settings.__dict__ or not settings.target_cities:
        settings.target_cities = list(CITY_BADGES.keys())

    col_all, col_reset, *city_cols = st.columns([1, 1] + [1.5] * len(CITY_BADGES))

    with col_all:
        if st.button("✅ Все", key="btn_city_all"):
            settings.target_cities = list(CITY_BADGES.keys())
            _save_target_cities()
            st.rerun()

    with col_reset:
        if st.button("❌ Сброс", key="btn_city_reset"):
            settings.target_cities = []
            _save_target_cities()
            st.rerun()

    for idx, (city_key, badge_label) in enumerate(CITY_BADGES.items()):
        with city_cols[idx]:
            is_active = city_key in settings.target_cities
            icon = "🟢" if is_active else "⚪"
            if st.button(f"{icon} {city_key}", key=f"btn_city_{city_key}"):
                if is_active:
                    settings.target_cities.remove(city_key)
                else:
                    settings.target_cities.append(city_key)
                _save_target_cities()
                st.rerun()


def _save_target_cities():
    """Save selected target cities to config JSON file."""
    import json
    with open(settings.target_cities_file, "w", encoding="utf-8") as f:
        json.dump(settings.target_cities, f, indent=2)


def render_main_content():
    """Render main trade analysis section."""
    st.title("⚔️ Albion Online Market Strategist Pro")
    st.caption("Сканер арбитража цен и ордеров (Азиатский Сервер — East)")

    render_city_selector()

    from src.db.engine import DatabaseEngine
    from src.services.trade_analyzer import get_trade_opportunities

    has_premium = st.session_state.get("premium", True)
    trade_mode = st.session_state.get("trade_mode", "order_flip")
    max_hours = st.session_state.get("hours", 6)

    tracked_items = settings.filtered_items or []

    engine = DatabaseEngine(settings.db_path)

    with st.spinner("🔍 Загрузка данных рынка..."):
        try:
            opportunities = get_trade_opportunities(
                db_path=settings.db_path,
                tracked_items=tracked_items,
                target_cities=settings.target_cities,
                has_premium=has_premium,
                max_hours_old=max_hours,
                trade_mode=trade_mode,
            )
        except Exception as e:
            st.error(f"❌ Ошибка загрузки арбитража: {e}")
            opportunities = []

    st.markdown("---")

    # Filter controls
    col_search, col_sort = st.columns([3, 2])
    with col_search:
        search_query = st.text_input(
            "🔍 Поиск предметов",
            placeholder="например: T5_ORE, FIBER, BAG, MEAL, SWORD",
            key="search_input",
        ).strip().upper()

    with col_sort:
        sort_by = st.selectbox(
            "📊 Сортировка",
            ["Прибыль (серебро)", "Маржа (%)", "Название предмета"],
            key="sort_select",
        )

    # Filter opportunities
    if search_query:
        opportunities = [
            op for op in opportunities
            if search_query in op["item"].upper() or search_query in op.get("item_name", "").upper()
        ]

    # Sort opportunities
    if sort_by == "Маржа (%)":
        opportunities.sort(key=lambda x: x["profit_percentage"], reverse=True)
    elif sort_by == "Название предмета":
        opportunities.sort(key=lambda x: x["item_name"])

    st.subheader(f"📊 Найдено: **{len(opportunities)}** (Городов: **{len(settings.target_cities)}** | Окно: **{max_hours} ч**)")

    if not opportunities:
        st.warning("⚠️ Нет выгодных связок с текущими фильтрами. Попробуйте увеличить окно свежести или добавить товары.")
        return

    # Render trade cards
    for op in opportunities[:100]:
        item_id = op["item"]
        item_name = op.get("item_name", item_id)
        buy_city = op["buy_city"]
        buy_price = op["buy_price"]
        buy_age = op.get("buy_age_mins", 0)
        sell_city = op["sell_city"]
        sell_price = op["sell_price"]
        sell_age = op.get("sell_age_mins", 0)
        net_profit = op["net_profit"]
        margin = op["profit_percentage"]

        card_col1, card_col2, card_col3, card_col4 = st.columns([1, 2.5, 2.5, 2])

        with card_col1:
            st.image(get_item_icon_url(item_id), width=60)

        with card_col2:
            st.markdown(f"**{item_name}**")
            st.caption(f"`ID: {item_id}` | Кач: {op['quality']}")
            st.caption(f"⏱️ Покупка: ~{buy_age} мин. | Продажа: ~{sell_age} мин.")

        with card_col3:
            st.markdown(f"<span class='buy-badge'>КУПИТЬ В: {buy_city}</span>", unsafe_allow_html=True)
            st.markdown(f"💰 Цена: **{buy_price:,.0f}** 🪙")

            st.markdown(f"<span class='sell-badge'>ПРОДАТЬ В: {sell_city}</span>", unsafe_allow_html=True)
            st.markdown(f"💰 Цена: **{sell_price:,.0f}** 🪙")

        with card_col4:
            st.markdown(f"<div class='profit-badge'>ЧИСТАЯ ПРИБЫЛЬ:<br>+{net_profit:,.0f} 🪙</div>", unsafe_allow_html=True)
            st.caption(f"Маржа: **+{margin:.1f}%**")

        st.markdown("<hr style='margin: 5px 0;'>", unsafe_allow_html=True)


def render_tracked_items():
    """Render tracked items manager tab."""
    st.title("📦 Управление отслеживаемыми предметами")

    from src.services.item_categorizer import get_categorized_items
    categories = get_categorized_items(settings.items_json_file)

    if not categories:
        st.info("💡 Файл catalog/items.json не найден. Используется встроенный список ресурсов.")
        return

    main_cats = list(categories.keys())
    selected_main = st.selectbox("🗂️ Главная категория", main_cats, key="main_cat_sel")

    sub_cats = list(categories[selected_main].keys())
    selected_sub = st.selectbox("📂 Подкатегория", sub_cats, key="sub_cat_sel")

    items_in_sub = categories[selected_main][selected_sub]

    st.write(f"Отображается предметов: **{len(items_in_sub)} шт**")

    btn_col1, btn_col2, btn_space = st.columns([1.2, 1.2, 4])

    with btn_col1:
        if st.button("✅ Выбрать все", key="btn_sel_all_cat"):
            for item_id in items_in_sub:
                if item_id not in settings.filtered_items:
                    settings.filtered_items.append(item_id)
            _save_tracked_items()
            st.toast("✅ Добавлены все предметы категории!")
            st.rerun()

    with btn_col2:
        if st.button("❌ Снять все", key="btn_clr_all_cat"):
            for item_id in items_in_sub:
                if item_id in settings.filtered_items:
                    settings.filtered_items.remove(item_id)
            _save_tracked_items()
            st.toast("🧹 Категория очищена!")
            st.rerun()

    st.markdown("<hr style='margin: 8px 0;'>", unsafe_allow_html=True)

    cols_per_row = 6
    rows = [items_in_sub[i:i + cols_per_row] for i in range(0, min(len(items_in_sub), 120), cols_per_row)]

    modified = False

    for row in rows:
        cols = st.columns(cols_per_row)
        for idx, item_id in enumerate(row):
            with cols[idx]:
                st.image(get_item_icon_url(item_id), width=55)
                st.caption(item_id)
                is_tracked = item_id in settings.filtered_items
                checked = st.checkbox("В списке", value=is_tracked, key=f"chk_{item_id}")

                if checked and not is_tracked:
                    settings.filtered_items.append(item_id)
                    modified = True
                elif not checked and is_tracked:
                    settings.filtered_items.remove(item_id)
                    modified = True

    if modified:
        _save_tracked_items()
        st.toast("✅ Список отслеживания обновлен!")


def _save_tracked_items():
    """Save tracked items to file."""
    import json
    with open(settings.filtered_items_file, "w", encoding="utf-8") as f:
        json.dump(settings.filtered_items, f, indent=2)


def run_sidebar():
    """Render the sidebar controls."""
    st.sidebar.header("⚙️ Стратегия & Настройки")

    has_premium = st.sidebar.checkbox("👑 Премиум-аккаунт", value=True, key="premium")

    trade_mode_label = st.sidebar.radio(
        "📊 Стратегия торговли",
        ["📜 Продажа по ордерам (Max Profit)", "⚡ Мгновенная сдача в Байордер"],
        key="trade_mode_label",
    )
    st.session_state["trade_mode"] = "instant" if "Мгновенная" in trade_mode_label else "order_flip"

    if st.session_state["trade_mode"] == "instant":
        tax_rate = 4.0 if has_premium else 8.0
    else:
        tax_rate = 6.5 if has_premium else 10.5
    st.sidebar.info(f"💡 Налог: **{tax_rate}%**")

    hours_options = {
        "1 час": 1,
        "3 часа": 3,
        "6 часов": 6,
        "12 часов": 12,
        "24 часа (Рекомендуется)": 24,
        "48 часов": 48,
    }
    selected_hours_label = st.sidebar.selectbox(
        "⏱️ Окно свежести",
        list(hours_options.keys()),
        index=4,
        key="hours_label",
    )
    st.session_state["hours"] = hours_options[selected_hours_label]

    st.sidebar.markdown("---")

    # Auto-collection
    auto_intervals = {
        "🛑 Выключено": 0,
        "⏱️ Каждую 1 мин": 60,
        "⏱️ Каждые 5 мин": 300,
        "⏱️ Каждые 15 мин": 900,
    }
    selected_auto = st.sidebar.selectbox(
        "🔄 Авто-обновление",
        list(auto_intervals.keys()),
        index=0,
        key="auto_label",
    )
    interval_sec = auto_intervals[selected_auto]

    from src.services.scheduler import Scheduler
    scheduler = Scheduler(settings.pid_file)

    if interval_sec > 0:
        if not scheduler.is_running():
            scheduler.start(interval=interval_sec)
            st.sidebar.success(f"🟢 Планировщик запущен ({interval_sec} сек)")
        else:
            st.sidebar.info("🟢 Планировщик активен")
    else:
        if scheduler.is_running():
            scheduler.stop()
            st.sidebar.warning("🛑 Планировщик остановлен")

    if st.sidebar.button("⚡ Собрать цены сейчас", key="btn_collect_now"):
        from src.workers.price_collector import PriceCollectorWorker
        with st.spinner("⏳ Сбор цен..."):
            worker = PriceCollectorWorker(db_path=settings.db_path)
            inserted = worker.run_once()
            st.sidebar.success(f"✅ Собрано: {inserted} записей!")
            st.rerun()


def main():
    """Main application entry point."""
    run_sidebar()

    tab_market, tab_items = st.tabs(["📊 Рынок & Арбитраж", "📦 Каталог Товаров"])

    with tab_market:
        render_main_content()

    with tab_items:
        render_tracked_items()


if __name__ == "__main__":
    main()
