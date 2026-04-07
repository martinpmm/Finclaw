"""Alpaca market data wrapper (free tier — 15-min delayed US equities)."""

from __future__ import annotations

from typing import Any

from finclaw.data.cache import TTLCache

_cache = TTLCache(default_ttl=60)  # 60s — delayed but stale data is still useless


def _get_client(api_key: str, secret_key: str):
    """Lazy-import and return an Alpaca StockHistoricalDataClient."""
    from alpaca.data import StockHistoricalDataClient
    return StockHistoricalDataClient(api_key=api_key, secret_key=secret_key)


def get_latest_quote(api_key: str, secret_key: str, symbol: str) -> dict[str, Any]:
    """Return the latest quote for a symbol (15-min delayed on free tier).

    Returns dict with keys: symbol, bid_price, bid_size, ask_price, ask_size,
    trade_price, trade_size, timestamp.
    """
    cache_key = f"alpaca:quote:{symbol.upper()}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from alpaca.data.requests import StockLatestQuoteRequest, StockLatestTradeRequest
        client = _get_client(api_key, secret_key)
        sym = symbol.upper()

        quote_req = StockLatestQuoteRequest(symbol_or_symbols=sym)
        trade_req = StockLatestTradeRequest(symbol_or_symbols=sym)
        quotes = client.get_stock_latest_quote(quote_req)
        trades = client.get_stock_latest_trade(trade_req)

        quote = quotes[sym]
        trade = trades[sym]

        result: dict[str, Any] = {
            "symbol": sym,
            "bid_price": float(quote.bid_price),
            "bid_size": int(quote.bid_size),
            "ask_price": float(quote.ask_price),
            "ask_size": int(quote.ask_size),
            "trade_price": float(trade.price),
            "trade_size": int(trade.size),
            "timestamp": str(quote.timestamp),
            "delayed": True,
        }
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        return {"error": str(e)}


def get_bars(
    api_key: str,
    secret_key: str,
    symbol: str,
    start: str,
    end: str,
    timeframe: str = "1Day",
) -> list[dict[str, Any]]:
    """Return OHLCV bars for a symbol.

    Args:
        timeframe: One of "1Min", "5Min", "15Min", "1Hour", "1Day".
    """
    cache_key = f"alpaca:bars:{symbol.upper()}:{start}:{end}:{timeframe}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        from datetime import datetime, timezone
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

        _tf_map = {
            "1Min": TimeFrame(1, TimeFrameUnit.Minute),
            "5Min": TimeFrame(5, TimeFrameUnit.Minute),
            "15Min": TimeFrame(15, TimeFrameUnit.Minute),
            "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
            "1Day": TimeFrame(1, TimeFrameUnit.Day),
        }
        tf = _tf_map.get(timeframe, TimeFrame(1, TimeFrameUnit.Day))

        client = _get_client(api_key, secret_key)
        sym = symbol.upper()

        req = StockBarsRequest(
            symbol_or_symbols=sym,
            timeframe=tf,
            start=datetime.fromisoformat(start).replace(tzinfo=timezone.utc),
            end=datetime.fromisoformat(end).replace(tzinfo=timezone.utc),
        )
        bars = client.get_stock_bars(req)
        result = [
            {
                "timestamp": str(bar.timestamp),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
                "vwap": float(bar.vwap) if bar.vwap else None,
            }
            for bar in bars[sym]
        ]
        _cache.set(cache_key, result, ttl=3600)
        return result
    except Exception as e:
        return [{"error": str(e)}]
