"""Memory query tool: search past financial analyses stored in institutional memory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class MemoryQueryTool(Tool):
    """Search and retrieve past financial analyses from institutional memory."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "memory_query"

    @property
    def description(self) -> str:
        return (
            "Search and retrieve past financial analyses from Finclaw's institutional memory. "
            "Every analysis Finclaw produces is stored, enabling questions like 'what did we "
            "think about NVDA's margin trajectory last quarter?' The memory persists across "
            "sessions and includes analyses, opinions, and events. "
            "Actions: search, history, store."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["search", "history", "store"],
                    "description": (
                        "search: find past analyses by keyword; "
                        "history: list recent analyses for a ticker; "
                        "store: save a new analysis to memory"
                    ),
                },
                "query": {
                    "type": "string",
                    "description": "Search query for 'search' action",
                },
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker for 'history' or 'store' action",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": [
                        "stock_analysis", "earnings_review", "thesis_update",
                        "sentiment_check", "regime_check", "portfolio_review",
                        "sec_filing_review", "opinion_change", "other",
                    ],
                    "description": "Type of analysis (for 'store' action)",
                },
                "content": {
                    "type": "string",
                    "description": "Analysis content to store",
                },
                "rating": {
                    "type": "string",
                    "enum": ["Bullish", "Neutral", "Bearish"],
                    "description": "Rating associated with the analysis",
                },
                "conviction": {
                    "type": "string",
                    "enum": ["High", "Medium", "Low"],
                    "description": "Conviction level",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of results to return. Default: 10.",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        from finclaw.data.memory_db import MemoryDB
        db = MemoryDB(self._workspace)

        if action == "search":
            return self._search(db, kwargs.get("query", ""), kwargs.get("limit", 10))
        if action == "history":
            return self._history(db, kwargs.get("ticker", ""), kwargs.get("limit", 10))
        if action == "store":
            return self._store(
                db,
                kwargs.get("ticker", ""),
                kwargs.get("analysis_type", "other"),
                kwargs.get("content", ""),
                kwargs.get("rating"),
                kwargs.get("conviction"),
            )
        return f"Unknown action: {action}"

    def _search(self, db, query: str, limit: int) -> str:
        if not query:
            return "Error: 'query' is required for search."

        results = db.search_analyses(query, limit)
        if not results:
            return f"No past analyses found matching '{query}'."

        lines = [f"## Memory Search: '{query}' ({len(results)} results)", ""]
        for r in results:
            rating_str = f" | {r.get('rating', '')}" if r.get("rating") else ""
            lines.append(f"**[{r['date']}] {r['ticker']} — {r['analysis_type']}**{rating_str}")
            # Show first 200 chars of content
            content_preview = r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"]
            lines.append(f"  {content_preview}")
            lines.append("")

        return "\n".join(lines)

    def _history(self, db, ticker: str, limit: int) -> str:
        if not ticker:
            return "Error: 'ticker' is required for history."

        results = db.query_analyses(ticker=ticker, limit=limit)
        if not results:
            return f"No past analyses found for {ticker.upper()}."

        lines = [f"## Analysis History: {ticker.upper()} ({len(results)} entries)", ""]
        for r in results:
            rating_str = f" [{r.get('rating', '')}]" if r.get("rating") else ""
            conviction_str = f" ({r.get('conviction', '')} conviction)" if r.get("conviction") else ""
            lines.append(f"**{r['date']}** — {r['analysis_type']}{rating_str}{conviction_str}")
            content_preview = r["content"][:300] + "..." if len(r["content"]) > 300 else r["content"]
            lines.append(f"  {content_preview}")
            lines.append("")

        return "\n".join(lines)

    def _store(self, db, ticker: str, analysis_type: str, content: str, rating: str | None, conviction: str | None) -> str:
        if not ticker:
            return "Error: 'ticker' is required for store."
        if not content:
            return "Error: 'content' is required for store."

        row_id = db.store_analysis(
            ticker=ticker,
            analysis_type=analysis_type,
            content=content,
            rating=rating,
            conviction=conviction,
        )
        return f"Stored {analysis_type} for {ticker.upper()} in institutional memory (ID: {row_id})."
