"""Investiny global securities tool — search and history via Investing.com."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class InvestinyGlobalTool(Tool):
    """Search global securities and fetch historical data via Investing.com (no API key required)."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "investiny_global"

    @property
    def description(self) -> str:
        return (
            "Search and fetch data for global securities via Investing.com — no API key required. "
            "Covers stocks, ETFs, indices, bonds, commodities, and crypto across all major markets. "
            "Actions: search (find securities by name/ticker), history (get historical OHLCV by asset ID)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "history"],
                    "description": (
                        "search: find securities by name or ticker across global markets; "
                        "history: fetch historical OHLCV data using the numeric ID from search results"
                    ),
                },
                "query": {
                    "type": "string",
                    "description": "Search query for 'search' action (e.g. 'Volkswagen', 'DAX', 'Gold')",
                },
                "n_results": {
                    "type": "integer",
                    "description": "Max search results to return. Default: 10.",
                    "minimum": 1,
                    "maximum": 50,
                },
                "investing_id": {
                    "type": "integer",
                    "description": "Numeric Investing.com asset ID from search results, required for 'history'",
                },
                "from_date": {
                    "type": "string",
                    "description": "Start date for history as MM/DD/YYYY. Defaults to 90 days ago.",
                },
                "to_date": {
                    "type": "string",
                    "description": "End date for history as MM/DD/YYYY. Defaults to today.",
                },
                "interval": {
                    "type": "string",
                    "enum": ["1min", "5min", "15min", "30min", "1hour", "5hour", "1day", "1week", "1month"],
                    "description": "Bar interval. Default: 1day.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        try:
            from finclaw.data import investiny
        except ImportError:
            return "Error: investiny is not installed. Install with: pip install finclaw[market-data]"

        if action == "search":
            query = kwargs.get("query", "")
            if not query:
                return "Error: 'query' is required for search."
            n = kwargs.get("n_results", 10)
            return self._search(investiny, query, n)

        if action == "history":
            investing_id = kwargs.get("investing_id")
            if not investing_id:
                return "Error: 'investing_id' is required for history. Run search first to get the ID."
            today = datetime.now()
            default_from = (today - timedelta(days=90)).strftime("%m/%d/%Y")
            default_to = today.strftime("%m/%d/%Y")
            from_date = kwargs.get("from_date", default_from)
            to_date = kwargs.get("to_date", default_to)
            interval = kwargs.get("interval", "1day")
            return self._history(investiny, int(investing_id), from_date, to_date, interval)

        return f"Unknown action: {action}"

    def _search(self, investiny_mod, query: str, n_results: int) -> str:
        results = investiny_mod.search_assets(query, n_results=n_results)
        if not results:
            return f"No results found for '{query}'."
        if "error" in results[0]:
            return f"Error searching for '{query}': {results[0]['error']}"

        lines = [
            f"## Search Results: '{query}'",
            "",
            "| ID | Name | Symbol | Exchange | Type | Country |",
            "|---|---|---|---|---|---|",
        ]
        for r in results:
            lines.append(
                f"| {r.get('id', '—')} | {r.get('name', '—')} | {r.get('symbol', '—')} | "
                f"{r.get('exchange', '—')} | {r.get('type', '—')} | {r.get('country', '—')} |"
            )
        lines.append("\n_Use the ID with action='history' to fetch price data._")
        return "\n".join(lines)

    def _history(self, investiny_mod, investing_id: int, from_date: str, to_date: str, interval: str) -> str:
        data = investiny_mod.get_history(investing_id, from_date, to_date, interval)
        if not data:
            return f"No history found for asset ID {investing_id}."
        if "error" in data[0]:
            return f"Error fetching history for ID {investing_id}: {data[0]['error']}"

        lines = [
            f"## History — Asset ID {investing_id} ({from_date} to {to_date}, {interval})",
            f"_Source: Investing.com via investiny_",
            "",
            "| Date | Open | High | Low | Close | Volume |",
            "|---|---|---|---|---|---|",
        ]
        for bar in data:
            vol_str = str(bar["volume"]) if bar.get("volume") else "—"
            lines.append(
                f"| {bar['date']} | {bar['open']} | {bar['high']} | "
                f"{bar['low']} | {bar['close']} | {vol_str} |"
            )

        if len(data) >= 2:
            try:
                first = float(data[0]["close"])
                last = float(data[-1]["close"])
                change = last - first
                pct = (change / first * 100) if first else 0
                lines.append(f"\n**Period return**: {change:+.2f} ({pct:+.2f}%)")
            except (ValueError, TypeError):
                pass

        return "\n".join(lines)
