"""Knowledge base tool: store and retrieve research documents and notes."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool

_HEADER = """\
# Knowledge Base

Research, reports, and documents that inform Finclaw's analysis and world view.
Finclaw extracts and stores only the most important insights from each document.

<!-- Documents will appear below as you share them -->
"""

_SOURCE_LABELS = {
    "earnings_call": "Earnings Call",
    "research_report": "Research Report",
    "annual_report": "Annual Report",
    "sec_filing": "SEC Filing",
    "news_article": "News Article",
    "analyst_note": "Analyst Note",
    "personal_note": "Personal Note",
    "other": "Document",
}


class DocumentsTool(Tool):
    """Store and retrieve research documents that inform financial analysis."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace
        self._file = workspace / "DOCUMENTS.md"

    @property
    def name(self) -> str:
        return "documents"

    @property
    def description(self) -> str:
        return (
            "Manage the research knowledge base — store documents, reports, and notes "
            "that inform Finclaw's opinions and analysis. "
            "When a user shares an earnings transcript, research report, annual report, "
            "news article, or any relevant text, extract the key insights and store them "
            "with action='ingest'. The knowledge base persists across sessions. "
            "Reference it when forming opinions on related stocks. "
            "Actions: ingest, list, get, delete, search."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["ingest", "list", "get", "delete", "search"],
                    "description": (
                        "ingest: store key notes from a document; "
                        "list: show all stored documents; "
                        "get: retrieve full notes for a document by title; "
                        "delete: remove a document; "
                        "search: find documents by keyword"
                    ),
                },
                "title": {
                    "type": "string",
                    "description": "Document title (e.g. 'Apple Q1 2026 Earnings Call', 'Goldman NVDA Initiation')",
                },
                "notes": {
                    "type": "string",
                    "description": (
                        "The most important insights extracted from the document, as concise bullet points. "
                        "Focus on facts, numbers, quotes, and forward-looking statements that could affect "
                        "stock analysis. 5-12 bullets recommended."
                    ),
                },
                "source_type": {
                    "type": "string",
                    "enum": [
                        "earnings_call",
                        "research_report",
                        "annual_report",
                        "sec_filing",
                        "news_article",
                        "analyst_note",
                        "personal_note",
                        "other",
                    ],
                    "description": "Type of document",
                },
                "tickers": {
                    "type": "string",
                    "description": "Comma-separated tickers this document is relevant to (e.g. 'AAPL,MSFT')",
                },
                "query": {
                    "type": "string",
                    "description": "Keyword or phrase to search for across all stored documents",
                },
            },
            "required": ["action"],
        }

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def execute(self, action: str, **kwargs: Any) -> str:
        if action == "ingest":
            return self._ingest(
                title=kwargs.get("title", ""),
                notes=kwargs.get("notes", ""),
                source_type=kwargs.get("source_type", "other"),
                tickers=kwargs.get("tickers", ""),
            )
        if action == "list":
            return self._list()
        if action == "get":
            return self._get(title=kwargs.get("title", ""))
        if action == "delete":
            return self._delete(title=kwargs.get("title", ""))
        if action == "search":
            return self._search(query=kwargs.get("query", ""))
        return f"Unknown action: {action}"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _ingest(self, title: str, notes: str, source_type: str, tickers: str) -> str:
        if not title:
            return "Error: 'title' is required for ingest."
        if not notes:
            return "Error: 'notes' is required for ingest. Extract the key insights first."

        content = self._read()
        today = date.today().isoformat()
        label = _SOURCE_LABELS.get(source_type, "Document")
        tickers_clean = ", ".join(t.strip().upper() for t in tickers.split(",") if t.strip())
        ticker_line = f" | **Tickers**: {tickers_clean}" if tickers_clean else ""

        # Remove existing entry with the same title if present (allows updates)
        start, end = self._find_section(content, title)
        if start != -1:
            content = content[:start] + content[end:]
            content = content.rstrip("\n") + "\n"

        # Build the new entry
        notes_formatted = "\n".join(
            f"- {line.lstrip('- ').strip()}" if line.strip() else ""
            for line in notes.strip().splitlines()
        )
        entry = (
            f"\n## [{today}] {title}\n"
            f"**Type**: {label}{ticker_line} | **Added**: {today}\n\n"
            f"{notes_formatted}\n\n"
            f"---\n"
        )

        content = content.rstrip("\n") + "\n" + entry
        self._write(content)

        ticker_msg = f" (relevant to {tickers_clean})" if tickers_clean else ""
        return f"Stored **{title}**{ticker_msg} in the knowledge base. Key notes saved."

    def _list(self) -> str:
        content = self._read()
        entries = self._parse_entries(content)
        if not entries:
            return "Knowledge base is empty. Share a document to add insights."

        lines = [f"## Knowledge Base ({len(entries)} documents)", ""]
        for e in entries:
            ticker_part = f" · {e['tickers']}" if e["tickers"] else ""
            lines.append(f"- **{e['title']}** ({e['type']}{ticker_part}) — {e['date']}")
        return "\n".join(lines)

    def _get(self, title: str) -> str:
        if not title:
            return "Error: 'title' is required."
        content = self._read()
        start, end = self._find_section(content, title)
        if start == -1:
            return f"No document found matching '{title}'. Use documents(action='list') to see all."
        return content[start:end].strip()

    def _delete(self, title: str) -> str:
        if not title:
            return "Error: 'title' is required."
        content = self._read()
        start, end = self._find_section(content, title)
        if start == -1:
            return f"No document found matching '{title}'."
        content = content[:start] + content[end:]
        self._write(content)
        return f"Removed **{title}** from the knowledge base."

    def _search(self, query: str) -> str:
        if not query:
            return "Error: 'query' is required."
        content = self._read()
        entries = self._parse_entries(content)
        results = []
        q = query.lower()
        for e in entries:
            start, end = self._find_section(content, e["title"])
            if start == -1:
                continue
            section = content[start:end]
            if q in section.lower():
                # Find matching lines
                matching = [
                    ln.strip()
                    for ln in section.splitlines()
                    if q in ln.lower() and ln.strip() and not ln.startswith("##")
                ]
                results.append((e["title"], e["date"], matching[:3]))

        if not results:
            return f"No documents found matching '{query}'."

        lines = [f"## Search results for '{query}' ({len(results)} documents)", ""]
        for title, doc_date, matches in results:
            lines.append(f"**{title}** ({doc_date})")
            for m in matches:
                lines.append(f"  › {m}")
            lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _read(self) -> str:
        if self._file.exists():
            return self._file.read_text(encoding="utf-8")
        return _HEADER

    def _write(self, content: str) -> None:
        self._file.write_text(content, encoding="utf-8")

    def _find_section(self, content: str, title: str) -> tuple[int, int]:
        """Return (start, end) char positions of the H2 section matching title, or (-1, -1)."""
        # Match ## [date] title or ## title (case-insensitive substring match)
        pattern = re.compile(r"^## .*?" + re.escape(title) + r".*?$", re.MULTILINE | re.IGNORECASE)
        m = pattern.search(content)
        if not m:
            return -1, -1
        start = m.start()
        # Find the next H2 section or end of file
        next_h2 = re.search(r"^## ", content[m.end():], re.MULTILINE)
        if next_h2:
            end = m.end() + next_h2.start()
        else:
            end = len(content)
        return start, end

    def _parse_entries(self, content: str) -> list[dict]:
        """Parse all document entries from DOCUMENTS.md."""
        entries = []
        for m in re.finditer(r"^## (\[(\d{4}-\d{2}-\d{2})\] )?(.+)$", content, re.MULTILINE):
            doc_date = m.group(2) or ""
            raw_title = m.group(3).strip()
            # Extract type and tickers from the line after the header
            start = m.end()
            next_h2 = re.search(r"^## ", content[start:], re.MULTILINE)
            section_end = start + next_h2.start() if next_h2 else len(content)
            section = content[start:section_end]
            type_match = re.search(r"\*\*Type\*\*: ([^|]+)", section)
            ticker_match = re.search(r"\*\*Tickers\*\*: ([^|]+)", section)
            entries.append(
                {
                    "title": raw_title,
                    "date": doc_date,
                    "type": type_match.group(1).strip() if type_match else "",
                    "tickers": ticker_match.group(1).strip() if ticker_match else "",
                }
            )
        return entries
