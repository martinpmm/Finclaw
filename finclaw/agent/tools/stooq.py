"""Stooq historical data tool — free global OHLCV history via pandas-datareader."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class StooqHistoryTool(Tool):
    """Fetch free global historical OHLCV data from Stooq (no API key required)."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "stooq_history"

    @property
    def description(self) -> str:
        return (
            "Fetch free global historical OHLCV data from Stooq — no API key required. "
            "Covers US, European, Asian, and other global markets. "
            "Use the exchange parameter for non-US symbols (e.g. exchange='DE' for German stocks). "
            "Actions: history."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["history"],
                    "description": "history: fetch historical daily OHLCV bars for a symbol",
                },
                "symbol": {
                    "type": "string",
                    "description": (
                        "Ticker symbol. For non-US stocks include the exchange suffix "
                        "(e.g. 'VOW3.DE') or use the exchange parameter."
                    ),
                },
                "start": {
                    "type": "string",
                    "description": "Start date as YYYY-MM-DD. Defaults to 90 days ago.",
                },
                "end": {
                    "type": "string",
                    "description": "End date as YYYY-MM-DD. Defaults to today.",
                },
                "exchange": {
                    "type": "string",
                    "description": (
                        "Exchange suffix to append: US (default), DE, UK, JP, HK, AU, CA, FR, IT, ES"
                    ),
                },
            },
            "required": ["action", "symbol"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        try:
            from finclaw.data import stooq
        except ImportError:
            return "Error: pandas-datareader is not installed. Install with: pip install finclaw[market-data]"

        symbol = kwargs.get("symbol", "")
        if not symbol:
            return "Error: 'symbol' is required."

        if action == "history":
            start = kwargs.get("start") or (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")
            end = kwargs.get("end") or datetime.now().strftime("%Y-%m-%d")
            exchange = kwargs.get("exchange")
            return self._history(stooq, symbol, start, end, exchange)
        return f"Unknown action: {action}"

    def _history(self, stooq_mod, symbol: str, start: str, end: str, exchange: str | None) -> str:
        data = stooq_mod.get_history(symbol, start, end, exchange)
        if not data:
            return f"No data found for {symbol} between {start} and {end}."
        if "error" in data[0]:
            return f"Error fetching history for {symbol}: {data[0]['error']}"

        stooq_sym = stooq_mod._stooq_symbol(symbol, exchange)
        lines = [
            f"## {stooq_sym} — Daily History ({start} to {end})",
            f"_Source: Stooq (free, no auth required)_",
            "",
            "| Date | Open | High | Low | Close | Volume |",
            "|---|---|---|---|---|---|",
        ]
        for bar in data:
            vol_str = f"{bar['volume']:,}" if bar["volume"] else "—"
            lines.append(
                f"| {bar['date']} | {bar['open']:.2f} | {bar['high']:.2f} | "
                f"{bar['low']:.2f} | {bar['close']:.2f} | {vol_str} |"
            )

        if len(data) >= 2:
            first = data[0]["close"]
            last = data[-1]["close"]
            change = last - first
            pct = (change / first * 100) if first else 0
            lines.append(f"\n**Period return**: {change:+.2f} ({pct:+.2f}%)")

        return "\n".join(lines)
