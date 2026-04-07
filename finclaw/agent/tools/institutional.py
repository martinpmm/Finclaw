"""Institutional holdings tool: track 13F filings and major fund positions."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool


class InstitutionalHoldingsTool(Tool):
    """Track institutional holdings via SEC 13F filings."""

    @property
    def name(self) -> str:
        return "institutional_holdings"

    @property
    def description(self) -> str:
        return (
            "Track institutional investor holdings via SEC 13F filings. "
            "See which major funds hold a stock, position changes quarter-over-quarter, "
            "and when big funds are accumulating or dumping positions. "
            "Example: 'Bridgewater added 400K shares of XYZ last quarter.' "
            "Actions: holders, search_fund."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["holders", "search_fund"],
                    "description": (
                        "holders: list top institutional holders of a stock; "
                        "search_fund: search 13F filings for a specific fund's positions"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (for 'holders' action)",
                },
                "fund_name": {
                    "type": "string",
                    "description": "Fund name to search for (for 'search_fund' action)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results. Default: 15.",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        if action == "holders":
            return await self._holders(kwargs.get("symbol", ""), kwargs.get("limit", 15))
        if action == "search_fund":
            return await self._search_fund(kwargs.get("fund_name", ""), kwargs.get("limit", 15))
        return f"Unknown action: {action}"

    async def _holders(self, symbol: str, limit: int) -> str:
        if not symbol:
            return "Error: 'symbol' is required."

        try:
            import yfinance as yf
        except ImportError:
            return "Error: yfinance not installed."

        symbol = symbol.upper()

        try:
            ticker = yf.Ticker(symbol)
            holders = ticker.institutional_holders

            if holders is None or holders.empty:
                return f"No institutional holder data found for {symbol}."

            lines = [
                f"## {symbol} — Top Institutional Holders",
                "",
                "| Holder | Shares | Value | % Out | Date |",
                "|---|---|---|---|---|",
            ]

            for _, row in holders.head(limit).iterrows():
                holder = str(row.get("Holder", "N/A"))[:40]
                shares = f"{int(row.get('Shares', 0)):,}" if row.get("Shares") else "N/A"
                value = f"${int(row.get('Value', 0)):,}" if row.get("Value") else "N/A"
                pct = f"{row.get('% Out', 0):.2f}%" if row.get("% Out") is not None else "N/A"
                date_rep = str(row.get("Date Reported", "N/A"))[:10]
                lines.append(f"| {holder} | {shares} | {value} | {pct} | {date_rep} |")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching institutional holders for {symbol}: {e}"

    async def _search_fund(self, fund_name: str, limit: int) -> str:
        if not fund_name:
            return "Error: 'fund_name' is required."

        try:
            from finclaw.data import edgar
        except ImportError:
            return "Error: edgartools not installed. Install with: pip install finclaw[market-intel]"

        try:
            from edgar import Company
            # Search for 13F filings by the fund
            # Note: This is a simplified approach - full 13F parsing requires more work
            results = edgar.search_filings(fund_name, form_type="13F-HR", limit=limit)

            if not results:
                return f"No 13F filings found for '{fund_name}'."

            lines = [
                f"## 13F Filings: {fund_name}",
                "",
                "| Date | Form | Description |",
                "|---|---|---|",
            ]
            for f in results:
                lines.append(f"| {f['filing_date']} | {f['form_type']} | {f.get('description', '')[:50]} |")

            lines.append(
                f"\nUse sec_filings(action='get_filing', symbol='{fund_name}', form_type='13F-HR') "
                "to read the full filing."
            )
            return "\n".join(lines)
        except Exception as e:
            return f"Error searching 13F filings: {e}"
