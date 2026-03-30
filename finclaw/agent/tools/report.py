"""Report generation tool: weekly reports, morning briefs, and equity research."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class ReportTool(Tool):
    """Generate formatted financial reports: weekly summaries, briefs, and equity research."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace
        self._reports_dir = workspace / "reports"

    @property
    def name(self) -> str:
        return "report"

    @property
    def description(self) -> str:
        return (
            "Generate formatted financial reports. Can produce weekly portfolio reports, "
            "enriched morning briefs, full equity research reports (inspired by institutional "
            "sell-side research), and custom reports. Reports can be output as markdown, HTML, "
            "or PDF. The tool handles assembly and formatting — you provide the analysis sections. "
            "Actions: weekly, morning_brief, equity_report, custom."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["weekly", "morning_brief", "equity_report", "custom"],
                    "description": (
                        "weekly: comprehensive weekly report; "
                        "morning_brief: enriched daily brief; "
                        "equity_report: institutional-grade equity research; "
                        "custom: user-specified sections"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Ticker for equity_report action",
                },
                "sections": {
                    "type": "string",
                    "description": (
                        "JSON array of sections for custom/weekly/equity reports. "
                        "Each section: {\"title\": \"...\", \"content\": \"...\"}"
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["markdown", "html", "pdf"],
                    "description": "Output format. Default: markdown.",
                },
                "title": {
                    "type": "string",
                    "description": "Report title. Auto-generated if omitted.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        fmt = kwargs.get("format", "markdown")
        title = kwargs.get("title", "")

        if action == "weekly":
            return self._generate(
                self._weekly_template(title), fmt, "weekly"
            )
        if action == "morning_brief":
            return self._generate(
                self._morning_brief_template(title), fmt, "morning_brief"
            )
        if action == "equity_report":
            symbol = kwargs.get("symbol", "")
            if not symbol:
                return "Error: 'symbol' is required for equity_report."
            return self._generate(
                self._equity_report_template(symbol.upper(), title), fmt, f"equity_{symbol.upper()}"
            )
        if action == "custom":
            sections_str = kwargs.get("sections", "")
            if not sections_str:
                return "Error: 'sections' is required for custom reports."
            return self._custom(sections_str, fmt, title)
        return f"Unknown action: {action}"

    def _generate(self, sections: list[dict], fmt: str, prefix: str) -> str:
        title = sections[0]["title"] if sections else "Finclaw Report"

        if fmt == "markdown":
            return self._to_markdown(sections)
        if fmt == "html":
            return self._to_html(sections, title)
        if fmt == "pdf":
            return self._to_pdf(sections, title, prefix)
        return self._to_markdown(sections)

    def _custom(self, sections_str: str, fmt: str, title: str) -> str:
        import json
        try:
            sections = json.loads(sections_str)
            if not isinstance(sections, list):
                return "Error: 'sections' must be a JSON array."
        except json.JSONDecodeError:
            return "Error: 'sections' must be valid JSON."

        report_title = title or "Custom Report"
        return self._generate(sections, fmt, "custom")

    def _to_markdown(self, sections: list[dict]) -> str:
        lines = []
        for s in sections:
            lines.append(f"# {s['title']}")
            lines.append("")
            lines.append(s["content"])
            lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def _to_html(self, sections: list[dict], title: str) -> str:
        try:
            from finclaw.data.report_renderer import render_html
            html = render_html(sections, title)

            # Save to file
            self._reports_dir.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{title.lower().replace(' ', '_')}_{date_str}.html"
            filepath = self._reports_dir / filename
            filepath.write_text(html, encoding="utf-8")

            return f"HTML report generated: {filepath}\n\n" + html[:2000] + "\n... [truncated]"
        except ImportError:
            return "Error: markdown library not installed. Install with: pip install finclaw[reports]"

    def _to_pdf(self, sections: list[dict], title: str, prefix: str) -> str:
        try:
            from finclaw.data.report_renderer import render_html, render_pdf

            html = render_html(sections, title)

            self._reports_dir.mkdir(parents=True, exist_ok=True)
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = f"{prefix}_{date_str}.pdf"
            filepath = self._reports_dir / filename

            render_pdf(html, filepath)
            return f"PDF report generated: {filepath}"
        except ImportError as e:
            return f"Error: {e}"

    # --- Report Templates ---

    def _weekly_template(self, title: str) -> list[dict]:
        title = title or f"Weekly Report — {datetime.now().strftime('%B %d, %Y')}"
        return [
            {"title": title, "content": "*Use other tools to populate each section below.*"},
            {"title": "Portfolio Performance", "content": (
                "Run `portfolio(action='summary')` and `portfolio(action='analyze')` to get:\n"
                "- Current positions and P&L\n"
                "- Sharpe ratio, max drawdown, weekly return\n"
                "- Allocation breakdown"
            )},
            {"title": "Macro Regime", "content": (
                "Run `macro_monitor(action='regime_check')` to get:\n"
                "- Current regime classification (risk-on/off, tightening/easing)\n"
                "- Key indicator changes from last week\n"
                "- Yield curve status"
            )},
            {"title": "Watchlist Updates", "content": (
                "Run `watchlist(action='list')` and check each stock:\n"
                "- Price changes >5% this week\n"
                "- Opinion changes\n"
                "- New thesis-relevant developments"
            )},
            {"title": "Sentiment Shifts", "content": (
                "Run `sentiment(action='daily_summary')` to see:\n"
                "- Stocks with biggest sentiment changes\n"
                "- News-driven sentiment shifts\n"
                "- Social media sentiment trends"
            )},
            {"title": "Upcoming Events", "content": (
                "Run `earnings_calendar(action='upcoming')` to list:\n"
                "- Earnings reports in the coming week\n"
                "- Fed meetings, economic data releases\n"
                "- Ex-dividend dates for portfolio stocks"
            )},
            {"title": "Thesis Status", "content": (
                "For each watchlist stock, summarize:\n"
                "- Current thesis validity\n"
                "- Confirm/challenge signals\n"
                "- Conviction level changes"
            )},
        ]

    def _morning_brief_template(self, title: str) -> list[dict]:
        title = title or f"Morning Brief — {datetime.now().strftime('%B %d, %Y')}"
        return [
            {"title": title, "content": "*Enriched morning brief with macro context and sentiment.*"},
            {"title": "Macro Context", "content": (
                "Run `macro_monitor(action='regime_check')` for current regime.\n"
                "Run `macro_monitor(action='yield_curve')` for rates context."
            )},
            {"title": "Market Overnight", "content": (
                "Run `sector_performance(period='1d')` for sector moves.\n"
                "Run `market_news()` for overnight developments."
            )},
            {"title": "Watchlist Sentiment", "content": (
                "Run `sentiment(action='analyze_stock')` for each watchlist stock.\n"
                "Highlight any sentiment shifts from previous day."
            )},
            {"title": "Today's Events", "content": (
                "Run `earnings_calendar(action='upcoming', days_ahead=1)` for today's earnings.\n"
                "Note any Fed speeches, economic data releases."
            )},
        ]

    def _equity_report_template(self, symbol: str, title: str) -> list[dict]:
        title = title or f"Equity Research: {symbol}"
        return [
            {"title": title, "content": f"*Institutional-grade equity research report for {symbol}.*"},
            {"title": "Executive Summary", "content": (
                f"Run `fundamentals(symbol='{symbol}')` and `stock_quote(symbol='{symbol}')` "
                "to form a concise investment thesis with target price and rating."
            )},
            {"title": "Business Overview", "content": (
                f"From `fundamentals(symbol='{symbol}')` extract:\n"
                "- Business description, sector, industry\n"
                "- Key products/services and competitive position\n"
                "- Management quality indicators"
            )},
            {"title": "Financial Analysis", "content": (
                f"Run `income_statement(symbol='{symbol}')`, `balance_sheet(symbol='{symbol}')`, "
                f"`cashflow(symbol='{symbol}')` to analyze:\n"
                "- Revenue trends and growth rates\n"
                "- Margin evolution\n"
                "- Cash flow generation\n"
                "- Balance sheet health"
            )},
            {"title": "Valuation", "content": (
                "From fundamentals compute:\n"
                "- DCF valuation (project FCF, apply WACC)\n"
                "- Peer comparison (P/E, EV/EBITDA, P/S)\n"
                "- Historical valuation range"
            )},
            {"title": "Technical Analysis", "content": (
                f"Run `technical_indicators(symbol='{symbol}')` and `stock_history(symbol='{symbol}')` for:\n"
                "- Trend analysis (SMA, EMA)\n"
                "- Momentum indicators (RSI, MACD)\n"
                "- Support/resistance levels"
            )},
            {"title": "Risk Assessment", "content": (
                "Identify and rank key risks:\n"
                "- Operational risks\n"
                "- Financial risks (leverage, liquidity)\n"
                "- Market/competitive risks\n"
                "- Regulatory risks"
            )},
            {"title": "Investment Recommendation", "content": (
                "Synthesize all sections into:\n"
                "- Rating (Buy/Hold/Sell)\n"
                "- Conviction level\n"
                "- Target price with upside/downside\n"
                "- Key catalysts and timeline"
            )},
        ]
