"""Alpaca market data tool — delayed US equity quotes and bars (free tier)."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class AlpacaMarketDataTool(Tool):
    """Fetch US equity quotes and historical bars from Alpaca (15-min delayed, free tier)."""

    def __init__(self, workspace: Path, api_key: str | None = None, secret_key: str | None = None) -> None:
        self._workspace = workspace
        self._api_key = api_key
        self._secret_key = secret_key

    @property
    def name(self) -> str:
        return "alpaca_market_data"

    @property
    def description(self) -> str:
        return (
            "Fetch US equity market data from Alpaca (free tier: 15-min delayed). "
            "Actions: quote (latest bid/ask/trade for a symbol), "
            "bars (historical OHLCV bars with configurable timeframe)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["quote", "bars"],
                    "description": (
                        "quote: get the latest delayed quote and trade for a symbol; "
                        "bars: get historical OHLCV bars for a symbol"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "US equity ticker symbol (e.g. AAPL, TSLA)",
                },
                "start": {
                    "type": "string",
                    "description": "Start date for bars as YYYY-MM-DD. Defaults to 30 days ago.",
                },
                "end": {
                    "type": "string",
                    "description": "End date for bars as YYYY-MM-DD. Defaults to today.",
                },
                "timeframe": {
                    "type": "string",
                    "enum": ["1Min", "5Min", "15Min", "1Hour", "1Day"],
                    "description": "Bar timeframe. Default: 1Day.",
                },
            },
            "required": ["action", "symbol"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        if not self._api_key or not self._secret_key:
            return (
                "Error: Alpaca API credentials not configured. "
                "Get free keys at https://alpaca.markets and add "
                "alpaca_api_key and alpaca_secret_key to your config under tools.financial_data."
            )

        try:
            from finclaw.data import alpaca
        except ImportError:
            return "Error: alpaca-py is not installed. Install with: pip install finclaw[market-data]"

        symbol = kwargs.get("symbol", "").upper()
        if not symbol:
            return "Error: 'symbol' is required."

        if action == "quote":
            return self._quote(alpaca, symbol)
        if action == "bars":
            start = kwargs.get("start") or (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            end = kwargs.get("end") or datetime.now().strftime("%Y-%m-%d")
            timeframe = kwargs.get("timeframe", "1Day")
            return self._bars(alpaca, symbol, start, end, timeframe)
        return f"Unknown action: {action}"

    def _quote(self, alpaca_mod, symbol: str) -> str:
        result = alpaca_mod.get_latest_quote(self._api_key, self._secret_key, symbol)
        if "error" in result:
            return f"Error fetching quote for {symbol}: {result['error']}"

        lines = [
            f"## {symbol} — Latest Quote (15-min delayed)",
            "",
            f"| Field | Value |",
            f"|---|---|",
            f"| Bid | ${result['bid_price']:.4f} x {result['bid_size']} |",
            f"| Ask | ${result['ask_price']:.4f} x {result['ask_size']} |",
            f"| Last Trade | ${result['trade_price']:.4f} x {result['trade_size']} |",
            f"| Timestamp | {result['timestamp']} |",
            "",
            "_Data is 15-minute delayed (Alpaca free tier)._",
        ]
        return "\n".join(lines)

    def _bars(self, alpaca_mod, symbol: str, start: str, end: str, timeframe: str) -> str:
        bars = alpaca_mod.get_bars(self._api_key, self._secret_key, symbol, start, end, timeframe)
        if not bars:
            return f"No bars found for {symbol} between {start} and {end}."
        if "error" in bars[0]:
            return f"Error fetching bars for {symbol}: {bars[0]['error']}"

        lines = [
            f"## {symbol} — {timeframe} Bars ({start} to {end})",
            "",
            "| Date | Open | High | Low | Close | Volume |",
            "|---|---|---|---|---|---|",
        ]
        for bar in bars:
            lines.append(
                f"| {bar['timestamp'][:10]} | {bar['open']:.2f} | {bar['high']:.2f} | "
                f"{bar['low']:.2f} | {bar['close']:.2f} | {bar['volume']:,} |"
            )

        if len(bars) >= 2:
            first_close = bars[0]["close"]
            last_close = bars[-1]["close"]
            change = last_close - first_close
            pct = (change / first_close * 100) if first_close else 0
            lines.append(f"\n**Period return**: {change:+.2f} ({pct:+.2f}%)")

        return "\n".join(lines)
