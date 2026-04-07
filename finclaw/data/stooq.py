"""Stooq historical market data via pandas-datareader (free, no auth)."""

from __future__ import annotations

from typing import Any

from finclaw.data.cache import TTLCache

_cache = TTLCache(default_ttl=3600)  # 1-hour cache for historical data

# Common exchange suffixes for Stooq symbol format
EXCHANGE_SUFFIXES = {
    "US": ".US",
    "DE": ".DE",
    "UK": ".UK",
    "JP": ".JP",
    "HK": ".HK",
    "AU": ".AU",
    "CA": ".CA",
    "FR": ".F",
    "IT": ".IT",
    "ES": ".ES",
}


def _stooq_symbol(symbol: str, exchange: str | None = None) -> str:
    """Format symbol for Stooq (e.g. 'AAPL' -> 'AAPL.US')."""
    sym = symbol.upper()
    if "." in sym:
        return sym  # Already has suffix
    if exchange:
        suffix = EXCHANGE_SUFFIXES.get(exchange.upper(), f".{exchange.upper()}")
        return f"{sym}{suffix}"
    return f"{sym}.US"  # Default to US


def get_history(
    symbol: str,
    start: str,
    end: str,
    exchange: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch daily OHLCV history from Stooq.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL', 'VOW3.DE').
        start:  Start date as 'YYYY-MM-DD'.
        end:    End date as 'YYYY-MM-DD'.
        exchange: Optional exchange code to append (e.g. 'US', 'DE', 'UK').

    Returns:
        List of {date, open, high, low, close, volume} dicts, oldest first.
    """
    stooq_sym = _stooq_symbol(symbol, exchange)
    cache_key = f"stooq:history:{stooq_sym}:{start}:{end}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        import pandas_datareader.data as web

        df = web.DataReader(stooq_sym, "stooq", start=start, end=end)
        if df.empty:
            return []

        # Stooq returns newest first — reverse to oldest first
        df = df.sort_index()
        result = [
            {
                "date": idx.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 4),
                "high": round(float(row["High"]), 4),
                "low": round(float(row["Low"]), 4),
                "close": round(float(row["Close"]), 4),
                "volume": int(row["Volume"]) if row["Volume"] else 0,
            }
            for idx, row in df.iterrows()
        ]
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        return [{"error": str(e)}]
