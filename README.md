# ⚔️ Albion Market Strategist Pro

Automated price and order arbitrage scanner for **Albion Online** (East / Asian Server), built with Python and Streamlit.

---

## 🌟 Key Features

- **⚡ Fast Batch Price Collection:** Optimized API queries retrieving thousands of market prices across all 7 Royal cities in ~5 seconds via batch requests to [Albion Online Data Project](https://www.albion-online-data.com/).
- **📊 Real-time Arbitrage Analysis:** Automatically calculates profitable cross-city buy/sell opportunities, factoring in sales tax rates (Premium vs. Standard) and setup fees.
- **🛡️ Enhanced Security:** Password authentication with SHA-256 / bcrypt hashing. Credentials and `.env` files are excluded from version control.
- **🌐 Responsive Web UI:** Modern Streamlit dashboard featuring item icons, city toggles, category filtering, search, and live price monitoring.
- **🔄 Cross-Platform Scheduler:** `psutil`-powered background price collector supporting both Windows and Linux environments (Ubuntu, server deployment ready).
- **🖥️ Dual Interface:** Run as an interactive Web App or via clean Command Line Interface (CLI).

---

## 🏗️ Project Architecture

```
albion_market_strategist/
├── src/                 # Single source of truth for all application code
│   ├── config/          # Pydantic configuration & environment settings
│   ├── api/             # AlbionOnlineData HTTP client & data models
│   ├── collectors/      # Batch price & catalog data collectors
│   ├── db/              # SQLite database engine, schema & migrations
│   ├── services/        # Business logic (trade analyzer, item categorizer, scheduler)
│   ├── workers/         # Background price collection worker
│   ├── bootstrap/       # Health checks & self-healing
│   ├── auth/            # Password authentication manager
│   └── ui/              # Streamlit Web UI & CLI interface
├── launcher.py          # Unified launcher (health check, scheduler, web UI)
├── tests/               # Pytest unit & regression suite
└── *.py                 # Legacy-compatible CLI entry points (thin wrappers)
```

---

## 🚀 Quick Start

### 1. Requirements & Installation

```bash
# Clone the repository
git clone https://github.com/AlanDyuk/test2.git
cd test2

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Available variables in `.env`:
- `APP_PASSWORD`: Password required to access the Streamlit Web UI (default: `albion2026`).
- `API_HOST`: Albion Online Data API host (default: `https://east.albion-online-data.com`).
- `SCHEDULER_INTERVAL`: Automatic collection interval in seconds (default: `300`).

---

## 🖥️ How to Run

### Option A: Interactive Windows Batch Script (Recommended for Windows)

Simply double-click `run.bat` or run in terminal:

```cmd
run.bat
```

Options included:
1. **Sync market prices** (`albion_data_collector.py`)
2. **Analyze trades** (`albion_trade_analyzer.py`)
3. **Filter resources** (`filter_items.py`)
4. **Start Streamlit Web UI**
5. **Start / Stop Background Scheduler**

### Option B: Command Line Commands

```bash
# 1. Filter resource item catalog
python filter_items.py

# 2. Run one-time price sync
python albion_data_collector.py --interval 0

# 3. Analyze trade opportunities
python albion_trade_analyzer.py --hours 6

# 4. Launch Streamlit Web UI
python -m streamlit run src/ui/streamlit/main.py
```

---

## 🔒 Security & Best Practices

- **Zero Price Filtering:** Automatically filters out missing/inactive market listings (`price = 0`).
- **SQL Injection Prevention:** Parameterized SQL queries throughout database operations.
- **Environment Isolation:** Local database (`albion_market.db`) and `.env` secrets are excluded from Git via `.gitignore`.

---

## 📜 License

MIT License — Free to use, modify, and distribute.
