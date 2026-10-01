"""Pydantic data models for Albion Online API responses."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class AlbionCity(BaseModel):
    """Represents an Albion Online city."""
    name: str
    emoji: str = ""
    display: str = ""

    @property
    def badge(self) -> str:
        return f"{self.emoji} {self.name}"

    @classmethod
    def from_dict(cls, name: str, emoji: str) -> "AlbionCity":
        return cls(name=name, emoji=emoji, display=f"{emoji} {name}")


class AlbionItem(BaseModel):
    """Represents an Albion Online item."""
    unique_name: str
    en_name: Optional[str] = None
    ru_name: Optional[str] = None
    item_type: Optional[str] = None
    tier: int = 0
    enchantment: int = 0
    quality: int = 0
    category: Optional[str] = None
    subcategory: Optional[str] = None


class MarketPrice(BaseModel):
    """A market price entry (sell or buy order)."""
    item_unique_name: str
    city_name: str
    quality: int
    sell_price_min: Optional[float] = None
    buy_price_max: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def age_minutes(self) -> float:
        now = datetime.now(timezone.utc)
        ts = self.timestamp if self.timestamp.tzinfo else self.timestamp.replace(tzinfo=timezone.utc)
        return (now - ts).total_seconds() / 60


class TradeOpportunity(BaseModel):
    """A profitable trade between two cities."""
    item_unique_name: str
    item_name: str  # display name
    buy_city: str
    buy_price: float
    sell_city: str
    sell_price: float
    quality: int
    net_profit: float
    profit_percentage: float
    age_minutes: float = 0.0
    is_premium: bool = True
    trade_mode: str = "order_flip"
