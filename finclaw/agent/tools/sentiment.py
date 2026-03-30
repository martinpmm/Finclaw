"""Sentiment analysis tool: FinBERT-powered financial sentiment scoring."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class SentimentTool(Tool):
    """Analyze financial sentiment using FinBERT on news headlines and text."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace
        self._cache_file = workspace / "sentiment_cache.json"

    @property
    def name(self) -> str:
        return "sentiment"

    @property
    def description(self) -> str:
        return (
            "Analyze financial sentiment using FinBERT, a BERT model fine-tuned on financial text. "
            "Can score stock news headlines to quantify sentiment (bullish/bearish/neutral), "
            "analyze arbitrary financial text, or show cached daily sentiment for watchlist stocks. "
            "This turns raw news into actionable signals like 'sentiment has shifted bearish on NVDA "
            "over the past 48 hours.' Actions: analyze_stock, analyze_text, daily_summary."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["analyze_stock", "analyze_text", "daily_summary"],
                    "description": (
                        "analyze_stock: score recent news headlines for a stock; "
                        "analyze_text: score user-supplied financial text; "
                        "daily_summary: show cached sentiment for all watchlist stocks"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (required for analyze_stock)",
                },
                "text": {
                    "type": "string",
                    "description": "Financial text to analyze (required for analyze_text)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of news headlines to analyze (default: 15, max: 50)",
                    "minimum": 1,
                    "maximum": 50,
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        try:
            from finclaw.data.sentiment import score_headlines, aggregate_sentiment
        except ImportError:
            return (
                "Error: FinBERT dependencies not installed. "
                "Install with: pip install finclaw[market-intel]"
            )

        if action == "analyze_stock":
            return await self._analyze_stock(
                kwargs.get("symbol", ""),
                kwargs.get("limit", 15),
                score_headlines,
                aggregate_sentiment,
            )
        if action == "analyze_text":
            return self._analyze_text(
                kwargs.get("text", ""),
                score_headlines,
                aggregate_sentiment,
            )
        if action == "daily_summary":
            return self._daily_summary()
        return f"Unknown action: {action}"

    async def _analyze_stock(
        self, symbol: str, limit: int, score_fn, aggregate_fn
    ) -> str:
        if not symbol:
            return "Error: 'symbol' is required for analyze_stock."

        try:
            import yfinance as yf
        except ImportError:
            return "Error: yfinance is not installed."

        symbol = symbol.upper()
        ticker = yf.Ticker(symbol)
        news = ticker.news

        if not news:
            return f"No recent news found for {symbol}."

        # Extract headlines
        headlines = []
        for item in news[:limit]:
            content = item.get("content", {})
            title = content.get("title") or item.get("title", "")
            if title:
                headlines.append(title)

        if not headlines:
            return f"No parseable headlines found for {symbol}."

        scored = score_fn(headlines)
        agg = aggregate_fn(scored)

        # Cache the result
        self._save_cache(symbol, agg, scored)

        lines = [
            f"## {symbol} — Sentiment Analysis ({len(scored)} headlines)",
            "",
            f"**Overall**: {agg['overall'].title()} (net score: {agg['net_score']:+.4f})",
            f"**Breakdown**: {agg['positive_count']} positive, "
            f"{agg['negative_count']} negative, {agg['neutral_count']} neutral",
            "",
            "### Headlines",
        ]

        for s in scored:
            emoji = {"positive": "+", "negative": "-", "neutral": "~"}[s["sentiment"]]
            lines.append(
                f"- [{emoji}] ({s['score']:.2f}) {s['text']}"
            )

        return "\n".join(lines)

    def _analyze_text(self, text: str, score_fn, aggregate_fn) -> str:
        if not text:
            return "Error: 'text' is required for analyze_text."

        # Split into sentences for granular scoring
        sentences = [s.strip() for s in text.replace("\n", ". ").split(". ") if s.strip()]
        if not sentences:
            return "Error: No analyzable text found."

        scored = score_fn(sentences)
        agg = aggregate_fn(scored)

        lines = [
            "## Text Sentiment Analysis",
            "",
            f"**Overall**: {agg['overall'].title()} (net score: {agg['net_score']:+.4f})",
            f"**Breakdown**: {agg['positive_count']} positive, "
            f"{agg['negative_count']} negative, {agg['neutral_count']} neutral",
            "",
            "### Sentence-level scores",
        ]

        for s in scored:
            emoji = {"positive": "+", "negative": "-", "neutral": "~"}[s["sentiment"]]
            lines.append(f"- [{emoji}] ({s['score']:.2f}) {s['text'][:120]}")

        return "\n".join(lines)

    def _daily_summary(self) -> str:
        if not self._cache_file.exists():
            return "No cached sentiment data. Run analyze_stock for watchlist stocks first."

        try:
            data = json.loads(self._cache_file.read_text(encoding="utf-8"))
        except Exception:
            return "Error reading sentiment cache."

        if not data:
            return "Sentiment cache is empty."

        lines = ["## Daily Sentiment Summary", "", "| Stock | Overall | Net Score | Headlines | Updated |", "|---|---|---|---|---|"]

        for symbol, entry in sorted(data.items()):
            agg = entry.get("aggregate", {})
            lines.append(
                f"| {symbol} | {agg.get('overall', 'N/A').title()} | "
                f"{agg.get('net_score', 0):+.4f} | {agg.get('total', 0)} | "
                f"{entry.get('updated', 'N/A')} |"
            )

        return "\n".join(lines)

    def _save_cache(self, symbol: str, aggregate: dict, scored: list) -> None:
        """Save sentiment result to daily cache."""
        try:
            if self._cache_file.exists():
                data = json.loads(self._cache_file.read_text(encoding="utf-8"))
            else:
                data = {}

            data[symbol] = {
                "aggregate": aggregate,
                "top_positive": [
                    s for s in sorted(scored, key=lambda x: x["scores"]["positive"], reverse=True)[:3]
                ],
                "top_negative": [
                    s for s in sorted(scored, key=lambda x: x["scores"]["negative"], reverse=True)[:3]
                ],
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }

            self._cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
