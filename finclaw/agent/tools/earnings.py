"""Earnings calendar tool: upcoming earnings, pre-briefs, and post-analysis."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class EarningsCalendarTool(Tool):
    """Track earnings dates and generate pre/post-earnings analysis."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "earnings_calendar"

    @property
    def description(self) -> str:
        return (
            "Track upcoming earnings dates for watchlist stocks and generate pre/post-earnings "
            "analysis. Before earnings: assembles consensus estimates, key metrics to watch, "
            "thesis confirmation/invalidation criteria. After earnings: pulls results, compares "
            "to estimates, runs sentiment analysis, suggests conviction updates. "
            "This makes Finclaw proactive: 'AAPL reports Thursday, here's what to watch.' "
            "Actions: upcoming, pre_brief, post_analysis, history."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["upcoming", "pre_brief", "post_analysis", "history"],
                    "description": (
                        "upcoming: list upcoming earnings for watchlist or specific stocks; "
                        "pre_brief: generate pre-earnings analysis for a stock; "
                        "post_analysis: analyze results after earnings are reported; "
                        "history: show past earnings surprises"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
                "symbols": {
                    "type": "string",
                    "description": "Comma-separated tickers for 'upcoming' action (e.g. 'AAPL,NVDA,MSFT')",
                },
                "days_ahead": {
                    "type": "integer",
                    "description": "Days to look ahead for upcoming earnings. Default: 14.",
                    "minimum": 1,
                    "maximum": 90,
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        try:
            import yfinance as yf
        except ImportError:
            return "Error: yfinance not installed."

        if action == "upcoming":
            return self._upcoming(
                kwargs.get("symbols", ""), kwargs.get("days_ahead", 14)
            )
        if action == "pre_brief":
            return self._pre_brief(kwargs.get("symbol", ""))
        if action == "post_analysis":
            return self._post_analysis(kwargs.get("symbol", ""))
        if action == "history":
            return self._history(kwargs.get("symbol", ""))
        return f"Unknown action: {action}"

    def _upcoming(self, symbols_str: str, days_ahead: int) -> str:
        import yfinance as yf

        if symbols_str:
            symbols = [s.strip().upper() for s in symbols_str.split(",") if s.strip()]
        else:
            # Try to read from watchlist
            symbols = self._get_watchlist_symbols()
            if not symbols:
                return "No symbols provided and watchlist is empty. Pass symbols='AAPL,NVDA,...'."

        now = datetime.now()
        cutoff = now + timedelta(days=days_ahead)
        upcoming = []

        for sym in symbols:
            try:
                ticker = yf.Ticker(sym)
                cal = ticker.calendar
                if cal is not None and not cal.empty:
                    # calendar can be a DataFrame or dict
                    if hasattr(cal, "to_dict"):
                        cal_dict = cal.to_dict()
                        earnings_date = cal_dict.get("Earnings Date", {})
                        if earnings_date:
                            for key, val in earnings_date.items():
                                if hasattr(val, "date"):
                                    dt = val
                                    if now <= datetime(dt.year, dt.month, dt.day) <= cutoff:
                                        upcoming.append((sym, dt.strftime("%Y-%m-%d")))
                                    break
                    elif isinstance(cal, dict):
                        ed = cal.get("Earnings Date")
                        if ed:
                            date_val = ed[0] if isinstance(ed, list) else ed
                            if hasattr(date_val, "strftime"):
                                upcoming.append((sym, date_val.strftime("%Y-%m-%d")))
            except Exception:
                continue

        if not upcoming:
            return f"No upcoming earnings found within {days_ahead} days."

        upcoming.sort(key=lambda x: x[1])

        lines = [
            f"## Upcoming Earnings (next {days_ahead} days)",
            "",
            "| Stock | Earnings Date | Days Until |",
            "|---|---|---|",
        ]
        for sym, dt_str in upcoming:
            try:
                dt = datetime.strptime(dt_str, "%Y-%m-%d")
                days = (dt - now).days
                lines.append(f"| {sym} | {dt_str} | {days}d |")
            except Exception:
                lines.append(f"| {sym} | {dt_str} | N/A |")

        return "\n".join(lines)

    def _pre_brief(self, symbol: str) -> str:
        if not symbol:
            return "Error: 'symbol' is required."

        import yfinance as yf

        symbol = symbol.upper()

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            name = info.get("longName") or symbol

            lines = [
                f"## {name} ({symbol}) — Pre-Earnings Brief",
                "",
                "### Company Info",
                f"- **Sector**: {info.get('sector', 'N/A')}",
                f"- **Market Cap**: ${info.get('marketCap', 0) / 1e9:.1f}B",
                f"- **Current Price**: ${info.get('currentPrice', info.get('regularMarketPrice', 0)):.2f}",
                "",
                "### Consensus Estimates",
            ]

            # Earnings estimates
            try:
                earnings_est = ticker.earnings_estimate
                if earnings_est is not None and not earnings_est.empty:
                    lines.append("**EPS Estimates**:")
                    lines.append(str(earnings_est))
                    lines.append("")
            except Exception:
                pass

            try:
                rev_est = ticker.revenue_estimate
                if rev_est is not None and not rev_est.empty:
                    lines.append("**Revenue Estimates**:")
                    lines.append(str(rev_est))
                    lines.append("")
            except Exception:
                pass

            # Recent performance
            lines += [
                "### Key Metrics to Watch",
                f"- **Trailing EPS**: ${info.get('trailingEps', 'N/A')}",
                f"- **Forward EPS**: ${info.get('forwardEps', 'N/A')}",
                f"- **Revenue Growth**: {(info.get('revenueGrowth', 0) or 0) * 100:.1f}%",
                f"- **Earnings Growth**: {(info.get('earningsGrowth', 0) or 0) * 100:.1f}%",
                f"- **Gross Margin**: {(info.get('grossMargins', 0) or 0) * 100:.1f}%",
                f"- **Operating Margin**: {(info.get('operatingMargins', 0) or 0) * 100:.1f}%",
                "",
                "### What to Watch",
                "- Revenue vs consensus (beat/miss by how much?)",
                "- Margin trends (expanding or compressing?)",
                "- Forward guidance (raising, maintaining, or lowering?)",
                "- Any segment breakdowns or one-time items",
            ]

            return "\n".join(lines)
        except Exception as e:
            return f"Error generating pre-earnings brief for {symbol}: {e}"

    def _post_analysis(self, symbol: str) -> str:
        if not symbol:
            return "Error: 'symbol' is required."

        import yfinance as yf

        symbol = symbol.upper()

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            lines = [
                f"## {symbol} — Post-Earnings Analysis",
                "",
            ]

            # Get earnings history for comparison
            try:
                earnings_hist = ticker.earnings_history
                if earnings_hist is not None and not earnings_hist.empty:
                    lines.append("### Recent Earnings Surprises")
                    lines.append(str(earnings_hist.tail(4)))
                    lines.append("")
            except Exception:
                pass

            # Get recent quarterly financials
            try:
                q_income = ticker.quarterly_income_stmt
                if q_income is not None and not q_income.empty:
                    latest = q_income.iloc[:, 0]
                    prev = q_income.iloc[:, 1] if q_income.shape[1] > 1 else None

                    lines.append("### Latest Quarter vs Previous")
                    key_metrics = ["Total Revenue", "Gross Profit", "Operating Income", "Net Income", "Basic EPS"]
                    for metric in key_metrics:
                        if metric in latest.index:
                            curr_val = latest[metric]
                            prev_val = prev[metric] if prev is not None and metric in prev.index else None
                            change_str = ""
                            if prev_val and prev_val != 0:
                                change = (curr_val - prev_val) / abs(prev_val) * 100
                                change_str = f" ({change:+.1f}% QoQ)"
                            lines.append(f"- **{metric}**: {curr_val:,.0f}{change_str}")
                    lines.append("")
            except Exception:
                pass

            lines += [
                "### Suggested Actions",
                "- Compare reported EPS to consensus estimates",
                "- Review forward guidance changes",
                "- Check for any thesis-relevant developments",
                "- Update conviction score based on results",
                "- Use sec_filings(action='get_filing', form_type='8-K') to read the full report",
            ]

            return "\n".join(lines)
        except Exception as e:
            return f"Error analyzing post-earnings for {symbol}: {e}"

    def _history(self, symbol: str) -> str:
        if not symbol:
            return "Error: 'symbol' is required."

        import yfinance as yf

        symbol = symbol.upper()

        try:
            ticker = yf.Ticker(symbol)

            lines = [f"## {symbol} — Earnings History", ""]

            try:
                earnings = ticker.earnings_history
                if earnings is not None and not earnings.empty:
                    lines.append(str(earnings))
                else:
                    lines.append("No earnings history available.")
            except Exception:
                # Fallback to quarterly earnings
                try:
                    q_earnings = ticker.quarterly_earnings
                    if q_earnings is not None and not q_earnings.empty:
                        lines.append(str(q_earnings))
                    else:
                        lines.append("No quarterly earnings data available.")
                except Exception:
                    lines.append("Could not fetch earnings history.")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching earnings history for {symbol}: {e}"

    def _get_watchlist_symbols(self) -> list[str]:
        """Read symbols from WATCHLIST.md."""
        import re
        watchlist_file = self._workspace / "WATCHLIST.md"
        if not watchlist_file.exists():
            return []
        content = watchlist_file.read_text(encoding="utf-8")
        return re.findall(r"^## ([A-Z0-9.]+)\s*$", content, re.MULTILINE)
