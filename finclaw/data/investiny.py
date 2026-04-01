"""Investiny data wrapper — global securities search and history via Investing.com."""

from __future__ import annotations

from typing import Any

from finclaw.data.cache import TTLCache

_cache = TTLCache(default_ttl=3600)  # 1-hour cache

# investiny interval codes
INTERVAL_MAP = {
    "1min": "1",
    "5min": "5",
    "15min": "15",
    "30min": "30",
    "1hour": "60",
    "5hour": "300",
    "1day": "D",
    "1week": "W",
    "1month": "M",
}


def search_assets(query: str, n_results: int = 10) -> list[dict[str, Any]]:
    """Search for securities on Investing.com.

    Returns list of dicts with keys: id, name, symbol, exchange, type, country.
    """
    cache_key = f"investiny:search:{query.lower()}:{n_results}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from investiny import search_assets as _search

        results = _search(query, n_results=n_results)
        _cache.set(cache_key, results)
        return results
    except Exception as e:
        return [{"error": str(e)}]


def get_history(
    investing_id: int,
    from_date: str,
    to_date: str,
    interval: str = "1day",
) -> list[dict[str, Any]]:
    """Fetch OHLCV history for an asset by its Investing.com ID.

    Args:
        investing_id: Numeric ID from search_assets() results.
        from_date:    Start date as 'MM/DD/YYYY'.
        to_date:      End date as 'MM/DD/YYYY'.
        interval:     One of: 1min, 5min, 15min, 30min, 1hour, 5hour, 1day, 1week, 1month.

    Returns:
        List of {date, open, high, low, close, volume} dicts.
    """
    interval_code = INTERVAL_MAP.get(interval.lower(), "D")
    cache_key = f"investiny:history:{investing_id}:{from_date}:{to_date}:{interval_code}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from investiny import historical_data

        data = historical_data(
            investing_id=investing_id,
            from_date=from_date,
            to_date=to_date,
            interval=interval_code,
        )
        # investiny returns dict of lists: {date: [...], open: [...], ...}
        dates = data.get("date", [])
        opens = data.get("open", [])
        highs = data.get("high", [])
        lows = data.get("low", [])
        closes = data.get("close", [])
        volumes = data.get("volume", [None] * len(dates))

        result = [
            {
                "date": dates[i],
                "open": opens[i],
                "high": highs[i],
                "low": lows[i],
                "close": closes[i],
                "volume": volumes[i],
            }
            for i in range(len(dates))
        ]
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        return [{"error": str(e)}]
