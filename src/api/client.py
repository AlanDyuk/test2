"""HTTP client for AlbionOnlineData API."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AlbionAPIError(Exception):
    """Base exception for API errors."""
    pass


class APIRateLimitError(AlbionAPIError):
    """Raised when the API rate limit is exceeded."""
    pass


class AlbionOnlineClient:
    """Synchronous HTTP client for the Albion Online Data API."""

    def __init__(self, base_url: str, timeout: float = 10.0,
                 retry_count: int = 3, retry_delay: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        """Lazy-initialized persistent client with connection pooling."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Execute a request with exponential backoff retry logic."""
        url = f"{self.base_url}{endpoint}"
        last_exception = None

        for attempt in range(1, self.retry_count + 1):
            try:
                client = self._get_client()
                response = client.request(method, url, **kwargs)

                if response.status_code == 429:
                    wait = float(response.headers.get("Retry-After", self.retry_delay))
                    logger.warning(f"Rate limit hit, waiting {wait}s (attempt {attempt})")
                    time.sleep(wait)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.TimeoutException:
                logger.warning(f"Timeout on attempt {attempt}/{self.retry_count}")
                last_exception = Exception(f"Request timed out: {url}")

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return {}  # No data for this item/city
                raise AlbionAPIError(f"HTTP {e.response.status_code}: {e}") from e

            except Exception as e:
                last_exception = e
                logger.warning(f"Attempt {attempt}/{self.retry_count} failed: {e}")

            if attempt < self.retry_count:
                # True exponential backoff: 1s, 2s, 4s, 8s...
                sleep_time = self.retry_delay * (2 ** (attempt - 1))
                time.sleep(sleep_time)

        raise last_exception or AlbionAPIError(f"All {self.retry_count} attempts failed for {url}")

    def close(self):
        """Close internal HTTP client session."""
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_prices_batch(self, items: List[str], cities: List[str]) -> List[Dict[str, Any]]:
        """Fetch batch prices for multiple items and cities in a single request."""
        if not items or not cities:
            return []
        items_str = ",".join(items)
        cities_str = ",".join(cities)
        endpoint = f"/api/v2/stats/prices/{items_str}.json?locations={cities_str}"
        result = self._request("GET", endpoint)
        return result if isinstance(result, list) else []

    def get_sell_orders(self, city: str, unique_name: str) -> List[Dict[str, Any]]:
        """Fetch sell orders for an item in a city."""
        result = self._request("GET", f"/api/v1/market/{city}/{unique_name}/sell-orders")
        return result if isinstance(result, list) else []

    def get_buy_orders(self, city: str, unique_name: str) -> List[Dict[str, Any]]:
        """Fetch buy orders for an item in a city."""
        result = self._request("GET", f"/api/v1/market/{city}/{unique_name}/buy-orders")
        return result if isinstance(result, list) else []

    def get_price_history(self, city: str, unique_name: str,
                          quality: int = 0) -> Dict[str, Any]:
        """Fetch price history for an item."""
        result = self._request("GET", f"/api/v1/market/{city}/{unique_name}/price-history")
        return result if isinstance(result, dict) else {}

    def get_all_items(self) -> List[Dict[str, Any]]:
        """Fetch the complete item catalog."""
        result = self._request("GET", "/api/v1/items")
        return result if isinstance(result, list) else []

    def get_cities(self) -> List[Dict[str, Any]]:
        """Fetch available cities."""
        result = self._request("GET", "/api/v1/cities")
        return result if isinstance(result, list) else []

    def get_items_json(self) -> List[Dict[str, Any]]:
        """Fetch the items JSON file (enriched with localized names)."""
        result = self._request("GET", "/api/v2/items?localized=RU-RU")
        return result if isinstance(result, list) else []
