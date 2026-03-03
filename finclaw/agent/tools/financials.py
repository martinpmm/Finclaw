"""Financial data tools: fundamentals, balance sheet, cash flow, income statement."""

from __future__ import annotations

from typing import Any

import pandas as pd

from finclaw.agent.tools.base import Tool


def _fmt_value(val: Any) -> str:
    """Format a financial value with B/M/K suffix."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    if isinstance(val, (int, float)):
        abs_val = abs(val)
        if abs_val >= 1e12:
            return f"${val/1e12:.2f}T"
        if abs_val >= 1e9:
            return f"${val/1e9:.2f}B"
        if abs_val >= 1e6:
            return f"${val/1e6:.2f}M"
        if abs_val >= 1e3:
            return f"${val/1e3:.2f}K"
        return f"${val:.2f}"
    return str(val)


def _fmt_pct(val: Any) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    return f"{val * 100:.1f}%"


class FundamentalsTool(Tool):
    """Get key fundamental metrics for a stock."""

    @property
    def name(self) -> str:
        return "fundamentals"

    @property
    def description(self) -> str:
        return (
            "Get key fundamental metrics for a stock: valuation ratios (P/E, P/B, EV/EBITDA), "
            "profitability (margins, ROE, ROA), growth rates, and business overview."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol (e.g. AAPL)"},
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            info = ticker.info

            name = info.get("longName") or info.get("shortName") or symbol.upper()
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            summary = info.get("longBusinessSummary", "")[:300] + "..." if info.get("longBusinessSummary") else ""

            lines = [
                f"## {name} ({symbol.upper()}) — Fundamentals",
                f"**Sector**: {sector}  |  **Industry**: {industry}",
                "",
                "### Valuation",
                f"- P/E (TTM): {info.get('trailingPE', 'N/A')}",
                f"- P/E (Forward): {info.get('forwardPE', 'N/A')}",
                f"- PEG Ratio: {info.get('pegRatio', 'N/A')}",
                f"- P/B Ratio: {info.get('priceToBook', 'N/A')}",
                f"- P/S Ratio: {info.get('priceToSalesTrailing12Months', 'N/A')}",
                f"- EV/EBITDA: {info.get('enterpriseToEbitda', 'N/A')}",
                f"- EV/Revenue: {info.get('enterpriseToRevenue', 'N/A')}",
                "",
                "### Profitability",
                f"- Gross Margin: {_fmt_pct(info.get('grossMargins'))}",
                f"- Operating Margin: {_fmt_pct(info.get('operatingMargins'))}",
                f"- Net Margin: {_fmt_pct(info.get('profitMargins'))}",
                f"- ROE: {_fmt_pct(info.get('returnOnEquity'))}",
                f"- ROA: {_fmt_pct(info.get('returnOnAssets'))}",
                "",
                "### Growth (YoY)",
                f"- Revenue Growth: {_fmt_pct(info.get('revenueGrowth'))}",
                f"- Earnings Growth: {_fmt_pct(info.get('earningsGrowth'))}",
                f"- EPS (TTM): ${info.get('trailingEps', 'N/A')}",
                f"- EPS (Forward): ${info.get('forwardEps', 'N/A')}",
                "",
                "### Financial Health",
                f"- Total Revenue: {_fmt_value(info.get('totalRevenue'))}",
                f"- Total Cash: {_fmt_value(info.get('totalCash'))}",
                f"- Total Debt: {_fmt_value(info.get('totalDebt'))}",
                f"- Debt/Equity: {info.get('debtToEquity', 'N/A')}",
                f"- Current Ratio: {info.get('currentRatio', 'N/A')}",
                f"- Free Cash Flow: {_fmt_value(info.get('freeCashflow'))}",
                "",
                "### Dividends & Buybacks",
                f"- Dividend Yield: {_fmt_pct(info.get('dividendYield'))}",
                f"- Payout Ratio: {_fmt_pct(info.get('payoutRatio'))}",
            ]

            if summary:
                lines += ["", "### Business Summary", summary]

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching fundamentals for {symbol}: {e}"


class BalanceSheetTool(Tool):
    """Get balance sheet data for a stock."""

    @property
    def name(self) -> str:
        return "balance_sheet"

    @property
    def description(self) -> str:
        return "Get balance sheet data (assets, liabilities, equity) for a stock, quarterly or annual."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "freq": {
                    "type": "string",
                    "enum": ["quarterly", "annual"],
                    "description": "Reporting frequency. Default: quarterly.",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, freq: str = "quarterly", **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            df = ticker.quarterly_balance_sheet if freq == "quarterly" else ticker.balance_sheet

            if df is None or df.empty:
                return f"No balance sheet data found for {symbol}."

            # Show last 4 periods
            df = df.iloc[:, :4]
            cols = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in df.columns]

            key_rows = [
                "Total Assets", "Total Liabilities Net Minority Interest",
                "Stockholders Equity", "Cash And Cash Equivalents",
                "Total Debt", "Current Assets", "Current Liabilities",
                "Inventory", "Accounts Receivable", "Long Term Debt",
            ]

            lines = [f"## {symbol.upper()} — Balance Sheet ({freq.title()})", ""]
            lines.append("| Item | " + " | ".join(cols) + " |")
            lines.append("|" + "---|" * (len(cols) + 1))

            for row in key_rows:
                if row in df.index:
                    vals = [_fmt_value(df.loc[row, c]) for c in df.columns]
                    lines.append(f"| {row} | " + " | ".join(vals) + " |")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching balance sheet for {symbol}: {e}"


class CashflowTool(Tool):
    """Get cash flow statement for a stock."""

    @property
    def name(self) -> str:
        return "cashflow"

    @property
    def description(self) -> str:
        return "Get cash flow statement (operating, investing, financing) for a stock, quarterly or annual."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "freq": {
                    "type": "string",
                    "enum": ["quarterly", "annual"],
                    "description": "Reporting frequency. Default: quarterly.",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, freq: str = "quarterly", **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            df = ticker.quarterly_cashflow if freq == "quarterly" else ticker.cashflow

            if df is None or df.empty:
                return f"No cash flow data found for {symbol}."

            df = df.iloc[:, :4]
            cols = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in df.columns]

            key_rows = [
                "Operating Cash Flow", "Free Cash Flow",
                "Capital Expenditure", "Investing Cash Flow",
                "Financing Cash Flow", "Net Income", "Depreciation And Amortization",
                "Stock Based Compensation", "Repurchase Of Capital Stock",
                "Cash Dividends Paid",
            ]

            lines = [f"## {symbol.upper()} — Cash Flow Statement ({freq.title()})", ""]
            lines.append("| Item | " + " | ".join(cols) + " |")
            lines.append("|" + "---|" * (len(cols) + 1))

            for row in key_rows:
                if row in df.index:
                    vals = [_fmt_value(df.loc[row, c]) for c in df.columns]
                    lines.append(f"| {row} | " + " | ".join(vals) + " |")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching cash flow for {symbol}: {e}"


class IncomeStatementTool(Tool):
    """Get income statement for a stock."""

    @property
    def name(self) -> str:
        return "income_statement"

    @property
    def description(self) -> str:
        return "Get income statement (revenue, expenses, profit) for a stock, quarterly or annual."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "freq": {
                    "type": "string",
                    "enum": ["quarterly", "annual"],
                    "description": "Reporting frequency. Default: quarterly.",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, freq: str = "quarterly", **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            df = ticker.quarterly_income_stmt if freq == "quarterly" else ticker.income_stmt

            if df is None or df.empty:
                return f"No income statement data found for {symbol}."

            df = df.iloc[:, :4]
            cols = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in df.columns]

            key_rows = [
                "Total Revenue", "Gross Profit", "Operating Income",
                "Net Income", "EBITDA", "Basic EPS", "Diluted EPS",
                "Research And Development", "Selling General And Administration",
                "Operating Expense", "Tax Provision",
            ]

            lines = [f"## {symbol.upper()} — Income Statement ({freq.title()})", ""]
            lines.append("| Item | " + " | ".join(cols) + " |")
            lines.append("|" + "---|" * (len(cols) + 1))

            for row in key_rows:
                if row in df.index:
                    vals = [_fmt_value(df.loc[row, c]) for c in df.columns]
                    lines.append(f"| {row} | " + " | ".join(vals) + " |")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching income statement for {symbol}: {e}"


class InsiderTransactionsTool(Tool):
    """Get recent insider transactions for a stock."""

    @property
    def name(self) -> str:
        return "insider_transactions"

    @property
    def description(self) -> str:
        return (
            "Get recent insider buying/selling activity for a stock. "
            "Useful for assessing insider confidence and spotting unusual activity."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            df = ticker.insider_transactions

            if df is None or df.empty:
                return f"No insider transaction data found for {symbol}."

            recent = df.head(15)
            lines = [f"## {symbol.upper()} — Recent Insider Transactions", ""]
            lines.append("| Date | Name | Title | Transaction | Shares | Value |")
            lines.append("|---|---|---|---|---|---|")

            for _, row in recent.iterrows():
                date = str(row.get("Start Date", row.get("Date", "N/A")))[:10]
                name = str(row.get("Name", "N/A"))[:25]
                title = str(row.get("Title", "N/A"))[:20]
                txn = str(row.get("Transaction", row.get("Text", "N/A")))
                shares = f"{int(row.get('Shares', 0)):,}" if row.get("Shares") else "N/A"
                value = _fmt_value(row.get("Value"))
                lines.append(f"| {date} | {name} | {title} | {txn} | {shares} | {value} |")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching insider transactions for {symbol}: {e}"
