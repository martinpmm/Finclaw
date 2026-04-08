"""Companies routes: watchlist CRUD + analysis data."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Request

router = APIRouter(tags=["companies"])

_WATCHLIST_FILE = "WATCHLIST.md"


def _load_watchlist(workspace: Path) -> str:
    p = workspace / _WATCHLIST_FILE
    return p.read_text(encoding="utf-8") if p.exists() else "# Stock Watchlist\n\n"


def _save_watchlist(workspace: Path, content: str) -> None:
    p = workspace / _WATCHLIST_FILE
    p.write_text(content, encoding="utf-8")


def _list_symbols(content: str) -> list[str]:
    return re.findall(r"^## ([A-Z0-9.\-^]+)\s*$", content, re.MULTILINE)


def _get_section(content: str, symbol: str) -> str | None:
    """Extract the full markdown section for a symbol."""
    pattern = rf"^## {re.escape(symbol.upper())}\s*$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return None
    start = match.start()
    next_h2 = re.search(r"^## ", content[match.end():], re.MULTILINE)
    end = match.end() + next_h2.start() if next_h2 else len(content)
    return content[start:end]


def _extract_field(section: str, field_name: str) -> str:
    pattern = rf"\*\*{re.escape(field_name)}\*\*:\s*(.+)"
    m = re.search(pattern, section)
    return m.group(1).strip() if m else ""


def _parse_company(section: str, symbol: str) -> dict:
    """Parse a watchlist section into a structured dict."""
    added = _extract_field(section, "Added")
    price = _extract_field(section, "Last Price")

    # Extract thesis
    thesis = ""
    thesis_match = re.search(r"### User Thesis\n(.*?)(?=\n###|\Z)", section, re.DOTALL)
    if thesis_match:
        thesis = thesis_match.group(1).strip()

    # Extract opinion
    opinion = ""
    opinion_match = re.search(r"### Agent Opinion\n(.*?)(?=\n###|\Z)", section, re.DOTALL)
    if opinion_match:
        opinion = opinion_match.group(1).strip()

    # Extract rating and conviction from opinion section
    rating = ""
    conviction = ""
    rating_match = re.search(r"\*\*Rating\*\*:\s*(\w+)", section)
    conviction_match = re.search(r"\*\*Conviction\*\*:\s*(\w+)", section)
    if rating_match:
        rating = rating_match.group(1)
    if conviction_match:
        conviction = conviction_match.group(1)

    # Extract recent notes
    notes = []
    notes_section = re.search(r"### Recent Notes\n(.*?)(?=\n##|\Z)", section, re.DOTALL)
    if notes_section:
        for line in notes_section.group(1).strip().split("\n"):
            line = line.strip()
            if line.startswith("- "):
                notes.append(line[2:])

    return {
        "symbol": symbol,
        "added": added,
        "price": price,
        "thesis": thesis,
        "opinion": opinion,
        "rating": rating,
        "conviction": conviction,
        "notes": notes,
    }


@router.get("/companies")
async def list_companies(request: Request):
    """List all companies on the watchlist."""
    workspace = request.app.state.workspace
    content = _load_watchlist(workspace)
    symbols = _list_symbols(content)

    companies = []
    for sym in symbols:
        section = _get_section(content, sym)
        if section:
            companies.append(_parse_company(section, sym))

    return {"companies": companies}


@router.get("/companies/{symbol}")
async def get_company(symbol: str, request: Request):
    """Get detailed information for a single company."""
    workspace = request.app.state.workspace
    content = _load_watchlist(workspace)
    section = _get_section(content, symbol.upper())

    if not section:
        return {"error": "Company not found", "symbol": symbol.upper()}

    company = _parse_company(section, symbol.upper())

    # Fetch analyses from MemoryDB
    try:
        from finclaw.data.memory_db import MemoryDB
        db = MemoryDB(workspace)
        analyses = db.query_analyses(ticker=symbol.upper(), limit=10)
        events = db.query_events(ticker=symbol.upper(), limit=10)
    except Exception:
        analyses = []
        events = []

    company["analyses"] = analyses
    company["events"] = events
    return company


@router.delete("/companies/{symbol}")
async def delete_company(symbol: str, request: Request):
    """Remove a company from the watchlist."""
    workspace = request.app.state.workspace
    content = _load_watchlist(workspace)
    sym = symbol.upper()

    pattern = rf"^## {re.escape(sym)}\s*$"
    match = re.search(pattern, content, re.MULTILINE)
    if not match:
        return {"error": "Company not found", "symbol": sym}

    start = match.start()
    next_h2 = re.search(r"^## ", content[match.end():], re.MULTILINE)
    end = match.end() + next_h2.start() if next_h2 else len(content)

    new_content = content[:start] + content[end:]
    _save_watchlist(workspace, new_content)

    return {"removed": sym}
