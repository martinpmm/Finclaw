"""SEC filings tool: search, read, and compare SEC EDGAR filings."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool


class SECFilingsTool(Tool):
    """Access SEC EDGAR filings: 10-K, 10-Q, 8-K, 13F and more."""

    @property
    def name(self) -> str:
        return "sec_filings"

    @property
    def description(self) -> str:
        return (
            "Search, read, and compare SEC EDGAR filings for any public company. "
            "Access 10-K (annual), 10-Q (quarterly), 8-K (current events), and 13F "
            "(institutional holdings) filings. Extract financial statements as formatted "
            "tables and compare metrics quarter-over-quarter. Uses the edgartools library "
            "which parses SEC filings into native Python objects. "
            "Actions: search, get_filing, financials, compare."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "get_filing", "financials", "compare"],
                    "description": (
                        "search: list recent filings for a ticker; "
                        "get_filing: read the text of a specific filing; "
                        "financials: extract financial statements as tables; "
                        "compare: compare metrics across recent filings"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL)",
                },
                "form_type": {
                    "type": "string",
                    "enum": ["10-K", "10-Q", "8-K", "13F-HR", "DEF 14A", "S-1"],
                    "description": "SEC form type. Default: 10-K.",
                },
                "index": {
                    "type": "integer",
                    "description": "Filing index (0=most recent, 1=second most recent). Default: 0.",
                    "minimum": 0,
                    "maximum": 10,
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of filings to return for search. Default: 5.",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["action", "symbol"],
        }

    async def execute(self, action: str, symbol: str = "", **kwargs: Any) -> str:
        if not symbol:
            return "Error: 'symbol' is required."

        try:
            from finclaw.data import edgar
        except ImportError:
            return (
                "Error: edgartools is not installed. "
                "Install with: pip install finclaw[market-intel]"
            )

        symbol = symbol.upper()
        form_type = kwargs.get("form_type", "10-K")
        index = kwargs.get("index", 0)
        limit = kwargs.get("limit", 5)

        if action == "search":
            return self._search(edgar, symbol, form_type, limit)
        if action == "get_filing":
            return self._get_filing(edgar, symbol, form_type, index)
        if action == "financials":
            return self._financials(edgar, symbol, form_type, index)
        if action == "compare":
            return self._compare(edgar, symbol, form_type)
        return f"Unknown action: {action}"

    def _search(self, edgar_mod, symbol: str, form_type: str, limit: int) -> str:
        try:
            filings = edgar_mod.search_filings(symbol, form_type, limit)
            if not filings:
                return f"No {form_type} filings found for {symbol}."

            lines = [
                f"## {symbol} — Recent {form_type} Filings",
                "",
                "| # | Date | Form | Description |",
                "|---|---|---|---|",
            ]
            for i, f in enumerate(filings):
                desc = f.get("description", "")[:60]
                lines.append(
                    f"| {i} | {f['filing_date']} | {f['form_type']} | {desc} |"
                )

            lines.append(
                f"\nUse `sec_filings(action='get_filing', symbol='{symbol}', "
                f"form_type='{form_type}', index=N)` to read a specific filing."
            )
            return "\n".join(lines)
        except Exception as e:
            return f"Error searching filings for {symbol}: {e}"

    def _get_filing(self, edgar_mod, symbol: str, form_type: str, index: int) -> str:
        try:
            result = edgar_mod.get_filing_text(symbol, form_type, index)
            if "error" in result:
                return result["error"]

            lines = [
                f"## {symbol} — {form_type} (filed {result['filing_date']})",
                f"**Accession**: {result['accession_number']}",
                "",
                result["text"],
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error reading filing for {symbol}: {e}"

    def _financials(self, edgar_mod, symbol: str, form_type: str, index: int) -> str:
        try:
            result = edgar_mod.get_financial_statements(symbol, form_type, index)
            if "error" in result:
                return result["error"]

            statements = result.get("statements", {})
            if not statements:
                return f"No financial statements found in {symbol} {form_type} filing."

            lines = [
                f"## {symbol} — Financial Statements from {form_type} (filed {result['filing_date']})",
                "",
            ]
            for stmt_name, stmt_data in statements.items():
                lines.append(f"### {stmt_name}")
                lines.append("")
                lines.append(stmt_data)
                lines.append("")

            return "\n".join(lines)
        except Exception as e:
            return f"Error extracting financials for {symbol}: {e}"

    def _compare(self, edgar_mod, symbol: str, form_type: str) -> str:
        try:
            result = edgar_mod.compare_filings(symbol, form_type, count=2)
            filings = result.get("filings", [])

            if len(filings) < 2:
                return f"Need at least 2 {form_type} filings to compare. Found {len(filings)}."

            lines = [
                f"## {symbol} — {form_type} Comparison (QoQ)",
                "",
            ]
            for i, f in enumerate(filings):
                label = "Most Recent" if i == 0 else "Previous"
                lines.append(f"### {label} ({f['filing_date']})")
                for stmt_name, stmt_data in f.get("statements", {}).items():
                    lines.append(f"#### {stmt_name}")
                    lines.append(stmt_data)
                    lines.append("")

            lines.append(
                "\n*Compare the tables above to identify trends in revenue, margins, "
                "cash flow, and balance sheet health.*"
            )
            return "\n".join(lines)
        except Exception as e:
            return f"Error comparing filings for {symbol}: {e}"
