"""
Application configuration using Pydantic BaseSettings.
Loaded from .env file (via python-dotenv) or environment variables.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, PrivateAttr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

try:
    from api.models import AlbionCity
except ImportError:
    from albion_strategist_refactor.api.models import AlbionCity


def _get_project_root() -> Path:
    curr = Path(__file__).resolve().parent
    for _ in range(5):
        if (curr / "pyproject.toml").exists() or (curr / ".git").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent

PROJECT_ROOT = _get_project_root()


class AppSettings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # App
    app_name: str = "Albion Market Strategist Pro"
    app_version: str = "0.1.0"

    # Authentication - bcrypt hash of "albion2026"
    hashed_password: str = Field(
        default="$2b$12$3ViL5Zz/CzSlzEeHmRkk1Ou8NvNbcOtXwhuAVGAeAUVwGGiipk4Fy"
    )

    # Albion Online API
    api_host: str = "https://east.albion-online-data.com"
    api_timeout: float = 10.0
    api_retry_count: int = 3
    api_retry_delay: float = 1.0

    # Scheduler
    scheduler_interval: int = 300  # seconds (5 min default)
    scheduler_auto_start: bool = False

    # Streamlit
    streamlit_port: int = 8501
    streamlit_address: str = "0.0.0.0"

    # Database
    db_path: str = Field(default="albion_market.db")

    # File paths
    filtered_items_file: str = Field(default="filtered_resource_items.json")
    target_cities_file: str = Field(default="selected_cities.json")
    items_json_file: str = Field(default="items.json")
    world_json_file: str = Field(default="world.json")
    pid_file: str = Field(default="scheduler_pid.txt")

    # Cities
    available_cities: List[AlbionCity] = Field(
        default_factory=lambda: [
            AlbionCity(name="Martlock", emoji="🌾"),
            AlbionCity(name="Thetford", emoji="🐸"),
            AlbionCity(name="Fort Sterling", emoji="🏰"),
            AlbionCity(name="Lymhurst", emoji="🌲"),
            AlbionCity(name="Bridgewatch", emoji="🏜️"),
            AlbionCity(name="Caerleon", emoji="💀"),
            AlbionCity(name="Brecilien", emoji="🌀"),
        ]
    )

    # Tax rates
    setup_fee: float = 0.025
    sales_tax_premium: float = 0.040
    sales_tax_standard: float = 0.080

    # Data retention
    max_data_age_hours: int = 48
    price_age_hours: int = 6

    # Trade analysis defaults
    trade_max_hours: int = 6
    default_trade_mode: str = "order_flip"  # "order_flip" or "instant"

    # Private attributes for dynamic item/city tracking
    _filtered_items_cache: Optional[List[str]] = PrivateAttr(default=None)
    _target_cities_cache: Optional[List[str]] = PrivateAttr(default=None)

    @property
    def filtered_items(self) -> List[str]:
        if self._filtered_items_cache is None:
            if os.path.exists(self.filtered_items_file):
                try:
                    import json
                    with open(self.filtered_items_file, "r", encoding="utf-8") as f:
                        self._filtered_items_cache = json.load(f)
                except Exception:
                    self._filtered_items_cache = []
            else:
                self._filtered_items_cache = []
        return self._filtered_items_cache

    @filtered_items.setter
    def filtered_items(self, value: List[str]):
        self._filtered_items_cache = value

    @property
    def target_cities(self) -> List[str]:
        if self._target_cities_cache is None:
            if os.path.exists(self.target_cities_file):
                try:
                    import json
                    with open(self.target_cities_file, "r", encoding="utf-8") as f:
                        self._target_cities_cache = json.load(f)
                except Exception:
                    self._target_cities_cache = [c.name for c in self.available_cities]
            else:
                self._target_cities_cache = [c.name for c in self.available_cities]
        return self._target_cities_cache

    @target_cities.setter
    def target_cities(self, value: List[str]):
        self._target_cities_cache = value

    @field_validator("db_path", "filtered_items_file", "target_cities_file", "items_json_file", "world_json_file", "pid_file", mode="after")
    @classmethod
    def _resolve_relative_paths(cls, v: str) -> str:
        """Resolve relative file paths relative to PROJECT_ROOT."""
        p = Path(v)
        if not p.is_absolute():
            return str(PROJECT_ROOT / p)
        return v

    @field_validator("hashed_password", mode="before")
    @classmethod
    def _ensure_hashed(cls, v):
        """If a raw password is provided, hash it with bcrypt."""
        if v and not v.startswith("$2b$") and not v.startswith("$2a$"):
            try:
                import bcrypt
                p_bytes = v.encode("utf-8")[:72]
                return bcrypt.hashpw(p_bytes, bcrypt.gensalt()).decode("utf-8")
            except ImportError:
                import hashlib
                return hashlib.sha256(v.encode("utf-8")).hexdigest()
        return v


def get_settings() -> AppSettings:
    """Singleton-like access to settings."""
    return AppSettings()


# Module-level singleton
settings = get_settings()
