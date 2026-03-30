"""SQLite-based institutional memory for financial analyses."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


class MemoryDB:
    """Persistent store for financial analyses and events."""

    def __init__(self, workspace: Path):
        self._db_path = workspace / "finclaw_memory.db"
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    analysis_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    rating TEXT,
                    conviction TEXT,
                    metadata_json TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_analyses_ticker ON analyses(ticker);
                CREATE INDEX IF NOT EXISTS idx_analyses_date ON analyses(date);

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticker TEXT NOT NULL,
                    date TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now'))
                );
                CREATE INDEX IF NOT EXISTS idx_events_ticker ON events(ticker);
                CREATE INDEX IF NOT EXISTS idx_events_date ON events(date);
            """)

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self._db_path))

    def store_analysis(
        self,
        ticker: str,
        analysis_type: str,
        content: str,
        rating: str | None = None,
        conviction: str | None = None,
        metadata: dict | None = None,
    ) -> int:
        """Store a financial analysis. Returns the row ID."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO analyses (ticker, date, analysis_type, content, rating, conviction, metadata_json) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (ticker.upper(), today, analysis_type, content, rating, conviction,
                 json.dumps(metadata) if metadata else None),
            )
            return cursor.lastrowid

    def store_event(self, ticker: str, event_type: str, summary: str) -> int:
        """Store a financial event. Returns the row ID."""
        today = datetime.now().strftime("%Y-%m-%d")
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO events (ticker, date, event_type, summary) VALUES (?, ?, ?, ?)",
                (ticker.upper(), today, event_type, summary),
            )
            return cursor.lastrowid

    def query_analyses(
        self,
        ticker: str | None = None,
        analysis_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query stored analyses with filters."""
        conditions = []
        params: list[Any] = []

        if ticker:
            conditions.append("ticker = ?")
            params.append(ticker.upper())
        if analysis_type:
            conditions.append("analysis_type = ?")
            params.append(analysis_type)
        if date_from:
            conditions.append("date >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("date <= ?")
            params.append(date_to)

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM analyses WHERE {where} ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def query_events(
        self,
        ticker: str | None = None,
        event_type: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Query stored events."""
        conditions = []
        params: list[Any] = []

        if ticker:
            conditions.append("ticker = ?")
            params.append(ticker.upper())
        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)

        where = " AND ".join(conditions) if conditions else "1=1"
        query = f"SELECT * FROM events WHERE {where} ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def search_analyses(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Full-text search across analysis content."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM analyses WHERE content LIKE ? ORDER BY date DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]
