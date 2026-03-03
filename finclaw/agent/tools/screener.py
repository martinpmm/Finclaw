"""Screener tools: sector performance, related tickers for discovery."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool

# Major sector ETFs for performance tracking
_SECTOR_ETFS = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Utilities": "XLU",
    "Real Estate": "XLRE",
    "Materials": "XLB",
    "Industrials": "XLI",
    "Communication Services": "XLC",
}

# Broad market benchmarks
_BENCHMARKS = {
    "S&P 500": "SPY",
    "Nasdaq 100": "QQQ",
    "Dow Jones": "DIA",
    "Russell 2000": "IWM",
    "VIX (Fear Index)": "^VIX",
    "10Y Treasury Yield": "^TNX",
    "Gold": "GLD",
    "Oil": "USO",
}


class SectorPerformanceTool(Tool):
    """Get performance of major market sectors and benchmarks."""

    @property
    def name(self) -> str:
        return "sector_performance"

    @property
    def description(self) -> str:
        return (
            "Get current performance of major market sectors (Technology, Healthcare, Energy, etc.) "
            "and key benchmarks (S&P 500, Nasdaq, VIX, Gold). "
            "Useful for identifying sector rotations, trends, and macro context. "
            "Use this to find which sectors are outperforming or underperforming."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
                    "description": "Time period for performance comparison. Default: 1mo.",
                },
            },
            "required": [],
        }

    async def execute(self, period: str = "1mo", **kwargs: Any) -> str:
        try:
            import yfinance as yf

            results: list[tuple[str, str, float]] = []

            all_symbols = {**_SECTOR_ETFS, **_BENCHMARKS}
            for name, sym in all_symbols.items():
                try:
                    hist = yf.Ticker(sym).history(period=period)
                    if hist.empty or len(hist) < 2:
                        continue
                    start = hist["Close"].iloc[0]
                    end = hist["Close"].iloc[-1]
                    pct = (end - start) / start * 100
                    results.append((name, sym, pct))
                except Exception:
                    continue

            if not results:
                return "Could not fetch sector performance data."

            # Sort by performance
            results.sort(key=lambda x: x[2], reverse=True)

            lines = [f"## Market & Sector Performance ({period})", ""]
            lines.append("### Sectors")
            lines.append("| Sector | ETF | Return |")
            lines.append("|---|---|---|")
            for name, sym, pct in results:
                if sym in _SECTOR_ETFS.values():
                    emoji = "🟢" if pct > 0 else "🔴"
                    lines.append(f"| {name} | {sym} | {emoji} {pct:+.2f}% |")

            lines.append("")
            lines.append("### Benchmarks & Macro")
            lines.append("| Index / Asset | Symbol | Return |")
            lines.append("|---|---|---|")
            for name, sym, pct in results:
                if sym in _BENCHMARKS.values():
                    emoji = "🟢" if pct > 0 else "🔴"
                    lines.append(f"| {name} | {sym} | {emoji} {pct:+.2f}% |")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching sector performance: {e}"


class RelatedTickersTool(Tool):
    """Find related stocks, peers, and ETFs for a given ticker."""

    @property
    def name(self) -> str:
        return "related_tickers"

    @property
    def description(self) -> str:
        return (
            "Find stocks, peers, competitors, and related ETFs for a given ticker. "
            "Use this to discover investment opportunities related to a stock you are already watching. "
            "Returns analyst recommendations and peer companies in the same sector."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol to find related tickers for (e.g. AAPL)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            info = ticker.info

            sector = info.get("sector", "")
            industry = info.get("industry", "")
            name = info.get("longName") or info.get("shortName") or symbol.upper()

            lines = [f"## Related to {name} ({symbol.upper()})", ""]

            if sector:
                lines.append(f"**Sector**: {sector}  |  **Industry**: {industry}")
                lines.append("")

            # Analyst recommendations
            try:
                recs = ticker.recommendations
                if recs is not None and not recs.empty:
                    recent = recs.tail(5)
                    lines.append("### Recent Analyst Recommendations")
                    lines.append("| Date | Firm | Grade | Action |")
                    lines.append("|---|---|---|---|")
                    for idx, row in recent.iterrows():
                        date = str(idx)[:10] if hasattr(idx, "__str__") else "N/A"
                        firm = str(row.get("Firm", row.get("firm", "N/A")))
                        grade = str(row.get("To Grade", row.get("toGrade", "N/A")))
                        action = str(row.get("Action", row.get("action", "N/A")))
                        lines.append(f"| {date} | {firm} | {grade} | {action} |")
                    lines.append("")
            except Exception:
                pass

            # Sector ETF
            sector_etf = _SECTOR_ETFS.get(sector)
            if sector_etf:
                lines.append(f"### Sector ETF")
                lines.append(f"- **{sector} ETF**: {sector_etf} — consider for broad sector exposure")
                lines.append("")

            # Suggest broad market ETFs
            lines.append("### Related Broad ETFs")
            lines.append("- **SPY** — S&P 500 (broad market exposure)")
            lines.append("- **QQQ** — Nasdaq 100 (tech/growth focused)")
            if sector == "Technology":
                lines.append("- **SOXX** — Semiconductor ETF")
                lines.append("- **IGV** — Software ETF")
                lines.append("- **ARKK** — Innovation/disruptive tech ETF")
            elif sector == "Healthcare":
                lines.append("- **IBB** — Biotech ETF")
                lines.append("- **XBI** — S&P Biotech ETF")
            elif sector == "Financials":
                lines.append("- **KBE** — Bank ETF")
                lines.append("- **KRE** — Regional Bank ETF")
            elif sector == "Energy":
                lines.append("- **XOP** — Oil & Gas Exploration ETF")
                lines.append("- **OIH** — Oil Services ETF")
            elif sector == "Consumer Discretionary":
                lines.append("- **XRT** — Retail ETF")

            # Top holdings if it's an ETF
            try:
                holdings = ticker.fund_top_holdings
                if holdings is not None and not holdings.empty:
                    lines.append("")
                    lines.append("### Top ETF Holdings")
                    for _, row in holdings.head(10).iterrows():
                        sym = row.get("Symbol", "N/A")
                        pct = row.get("% Assets", row.get("holdingPercent", 0))
                        holding_name = row.get("Name", row.get("holdingName", sym))
                        lines.append(f"- {sym}: {holding_name} ({pct:.1f}%)")
            except Exception:
                pass

            return "\n".join(lines)

        except Exception as e:
            return f"Error finding related tickers for {symbol}: {e}"
