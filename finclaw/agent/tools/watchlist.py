"""Watchlist tool: manage the user's stock watchlist with theses and agent opinions."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool

_WATCHLIST_FILE = "WATCHLIST.md"


def _load(workspace: Path) -> str:
    p = workspace / _WATCHLIST_FILE
    if p.exists():
        return p.read_text(encoding="utf-8")
    return "# Stock Watchlist\n\n"


def _save(workspace: Path, content: str) -> None:
    p = workspace / _WATCHLIST_FILE
    p.write_text(content, encoding="utf-8")


def _get_stock_section(content: str, symbol: str) -> tuple[int, int] | None:
    """Return (start, end) character indices of a stock's H2 section, or None."""
    pattern = rf"^## {re.escape(symbol.upper())}\s*$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return None
    start = match.start()
    # Find the next H2 heading or end of file
    next_h2 = re.search(r"^## ", content[match.end():], re.MULTILINE)
    end = match.end() + next_h2.start() if next_h2 else len(content)
    return start, end


def _extract_field(section: str, field_name: str) -> str:
    """Extract a named field value from a section (e.g. '- **Field**: value')."""
    pattern = rf"\*\*{re.escape(field_name)}\*\*:\s*(.+)"
    m = re.search(pattern, section)
    return m.group(1).strip() if m else ""


def _list_symbols(content: str) -> list[str]:
    return re.findall(r"^## ([A-Z0-9.\-^]+)\s*$", content, re.MULTILINE)


def _build_stock_section(
    symbol: str,
    thesis: str = "",
    opinion: str = "",
    rating: str = "",
    conviction: str = "",
    notes: str = "",
    price: str = "",
    added: str = "",
) -> str:
    today = date.today().isoformat()
    added = added or today
    price_line = f"- **Last Price**: {price}\n" if price else ""
    thesis_content = thesis or "_No thesis provided yet. Tell me why you find this stock interesting!_"
    opinion_content = opinion or "_No opinion formed yet. Add stock to trigger initial analysis._"
    rating_line = f"**Rating**: {rating} | **Conviction**: {conviction} | **Updated**: {today}\n" if rating else ""
    notes_line = f"- [{today}] {notes}\n" if notes else f"- [{today}] Added to watchlist\n"

    return (
        f"## {symbol.upper()}\n"
        f"- **Added**: {added}\n"
        f"{price_line}"
        f"\n### User Thesis\n{thesis_content}\n"
        f"\n### Agent Opinion\n{rating_line}{opinion_content}\n"
        f"\n### Recent Notes\n{notes_line}"
    )


class WatchlistTool(Tool):
    """Manage the stock watchlist: add, remove, update thesis and opinions."""

    def __init__(self, workspace: Path):
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "watchlist"

    @property
    def description(self) -> str:
        return (
            "Manage the stock watchlist. Actions:\n"
            "- add: Add a stock to watch\n"
            "- remove: Remove a stock\n"
            "- list: List all watched stocks with current ratings\n"
            "- get: Get full details for one stock (thesis, opinion, notes)\n"
            "- update_thesis: Update the user's investment thesis for a stock\n"
            "- update_opinion: Update the agent's opinion and rating for a stock\n"
            "- add_note: Add a timestamped note to a stock's history"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "remove", "list", "get", "update_thesis", "update_opinion", "add_note"],
                    "description": "Action to perform on the watchlist",
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (required for all actions except 'list')",
                },
                "thesis": {
                    "type": "string",
                    "description": "User's investment thesis (for update_thesis or add)",
                },
                "opinion": {
                    "type": "string",
                    "description": "Agent's opinion text (for update_opinion)",
                },
                "rating": {
                    "type": "string",
                    "enum": ["Bullish", "Neutral", "Bearish"],
                    "description": "Agent's rating (for update_opinion)",
                },
                "conviction": {
                    "type": "string",
                    "enum": ["High", "Medium", "Low"],
                    "description": "Agent's conviction level (for update_opinion)",
                },
                "note": {
                    "type": "string",
                    "description": "Note text to add to the stock's history (for add_note)",
                },
                "price": {
                    "type": "string",
                    "description": "Current price string to record (for add or add_note), e.g. '$242.50'",
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str,
        symbol: str = "",
        thesis: str = "",
        opinion: str = "",
        rating: str = "",
        conviction: str = "",
        note: str = "",
        price: str = "",
        **kwargs: Any,
    ) -> str:
        content = _load(self._workspace)
        symbol = symbol.upper() if symbol else ""

        if action == "list":
            symbols = _list_symbols(content)
            if not symbols:
                return "Your watchlist is empty. Say something like 'Add AAPL to my watchlist' to start tracking stocks."
            lines = ["## Your Watchlist", ""]
            for sym in symbols:
                idx = _get_stock_section(content, sym)
                if idx:
                    section = content[idx[0]:idx[1]]
                    r = _extract_field(section, "Rating")
                    conv = _extract_field(section, "Conviction")
                    last_price = _extract_field(section, "Last Price")
                    rating_str = f" — {r}" + (f" ({conv} conviction)" if conv else "") if r else ""
                    price_str = f" | {last_price}" if last_price else ""
                    lines.append(f"- **{sym}**{rating_str}{price_str}")
            return "\n".join(lines)

        if not symbol:
            return "Error: 'symbol' is required for this action."

        if action == "add":
            if _get_stock_section(content, symbol):
                return f"{symbol} is already in your watchlist."
            section = _build_stock_section(symbol, thesis=thesis, price=price)
            if not content.endswith("\n"):
                content += "\n"
            content += "\n" + section
            _save(self._workspace, content)
            return f"Added **{symbol}** to your watchlist. {('Thesis saved.' if thesis else 'You can share your investment thesis anytime.')}"

        if action == "remove":
            idx = _get_stock_section(content, symbol)
            if not idx:
                return f"{symbol} is not in your watchlist."
            content = content[:idx[0]] + content[idx[1]:]
            content = content.rstrip() + "\n"
            _save(self._workspace, content)
            return f"Removed **{symbol}** from your watchlist."

        if action == "get":
            idx = _get_stock_section(content, symbol)
            if not idx:
                return f"{symbol} is not in your watchlist. Use action='add' to add it."
            return content[idx[0]:idx[1]].strip()

        if action == "update_thesis":
            if not thesis:
                return "Error: 'thesis' is required for update_thesis."
            idx = _get_stock_section(content, symbol)
            if not idx:
                return f"{symbol} is not in your watchlist. Add it first."
            section = content[idx[0]:idx[1]]
            # Replace the User Thesis subsection
            new_section = re.sub(
                r"(### User Thesis\n).*?(\n### )",
                rf"\g<1>{thesis}\n\2",
                section,
                flags=re.DOTALL,
            )
            if new_section == section:
                # Fallback: append if pattern not matched
                new_section = section.rstrip() + f"\n\n### User Thesis\n{thesis}\n"
            content = content[:idx[0]] + new_section + content[idx[1]:]
            _save(self._workspace, content)
            return f"Updated investment thesis for **{symbol}**."

        if action == "update_opinion":
            idx = _get_stock_section(content, symbol)
            if not idx:
                return f"{symbol} is not in your watchlist. Add it first."
            today = date.today().isoformat()
            section = content[idx[0]:idx[1]]
            rating_line = f"**Rating**: {rating} | **Conviction**: {conviction} | **Updated**: {today}\n" if rating else ""
            new_opinion_block = f"### Agent Opinion\n{rating_line}{opinion}\n"
            new_section = re.sub(
                r"### Agent Opinion\n.*?(\n### |\Z)",
                lambda m: new_opinion_block + (m.group(1) if m.group(1).strip() else ""),
                section,
                flags=re.DOTALL,
            )
            if new_section == section:
                new_section = section.rstrip() + f"\n\n{new_opinion_block}"
            content = content[:idx[0]] + new_section + content[idx[1]:]
            _save(self._workspace, content)
            rating_str = f" Rating: **{rating}**" + (f" ({conviction} conviction)" if conviction else "") if rating else ""
            return f"Updated opinion for **{symbol}**.{rating_str}"

        if action == "add_note":
            if not note and not price:
                return "Error: 'note' or 'price' is required for add_note."
            idx = _get_stock_section(content, symbol)
            if not idx:
                return f"{symbol} is not in your watchlist. Add it first."
            today = date.today().isoformat()
            section = content[idx[0]:idx[1]]

            # Update price field
            if price:
                if re.search(r"\*\*Last Price\*\*:", section):
                    section = re.sub(r"\*\*Last Price\*\*: .+", f"**Last Price**: {price}", section)
                else:
                    section = re.sub(r"(- \*\*Added\*\*: .+\n)", rf"\g<1>- **Last Price**: {price}\n", section)

            # Add note to Recent Notes
            note_entry = f"- [{today}]"
            if price:
                note_entry += f" Price: {price}"
            if note:
                note_entry += f" {note}"
            note_entry += "\n"

            if "### Recent Notes" in section:
                section = section.replace("### Recent Notes\n", f"### Recent Notes\n{note_entry}")
            else:
                section = section.rstrip() + f"\n\n### Recent Notes\n{note_entry}"

            content = content[:idx[0]] + section + content[idx[1]:]
            _save(self._workspace, content)
            return f"Note added to **{symbol}**."

        return f"Unknown action: {action}"
