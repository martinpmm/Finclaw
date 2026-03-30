"""Social sentiment tool: Reddit financial sentiment via PRAW + FinBERT."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool

_DEFAULT_SUBREDDITS = ["wallstreetbets", "stocks", "investing"]


class SocialSentimentTool(Tool):
    """Track social media sentiment on stocks from financial Reddit communities."""

    def __init__(
        self,
        workspace: Path,
        reddit_client_id: str = "",
        reddit_client_secret: str = "",
        reddit_user_agent: str = "finclaw/1.0",
    ) -> None:
        self._workspace = workspace
        self._client_id = reddit_client_id
        self._client_secret = reddit_client_secret
        self._user_agent = reddit_user_agent

    @property
    def name(self) -> str:
        return "social_sentiment"

    @property
    def description(self) -> str:
        return (
            "Track social media sentiment from financial Reddit communities "
            "(r/wallstreetbets, r/stocks, r/investing). Fetches recent posts mentioning "
            "a stock, scores them with FinBERT, and returns mention count, average sentiment, "
            "and top bullish/bearish posts. Actions: reddit, summary."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["reddit", "summary"],
                    "description": (
                        "reddit: scan Reddit for mentions of a stock; "
                        "summary: show cached social sentiment for all recently scanned stocks"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol to search for",
                },
                "subreddit": {
                    "type": "string",
                    "description": "Specific subreddit to search (default: scans wallstreetbets, stocks, investing)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max posts to analyze per subreddit. Default: 25.",
                    "minimum": 5,
                    "maximum": 100,
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        if action == "reddit":
            return self._reddit(
                kwargs.get("symbol", ""),
                kwargs.get("subreddit", ""),
                kwargs.get("limit", 25),
            )
        if action == "summary":
            return self._summary()
        return f"Unknown action: {action}"

    def _reddit(self, symbol: str, subreddit: str, limit: int) -> str:
        if not symbol:
            return "Error: 'symbol' is required."
        if not self._client_id or not self._client_secret:
            return (
                "Error: Reddit API credentials not configured. "
                "Create a free app at https://www.reddit.com/prefs/apps and add "
                "reddit_client_id and reddit_client_secret to your Finclaw config."
            )

        try:
            import praw
        except ImportError:
            return "Error: praw not installed. Install with: pip install finclaw[alt-data]"

        try:
            from finclaw.data.sentiment import score_headlines, aggregate_sentiment
        except ImportError:
            return "Error: FinBERT not installed. Install with: pip install finclaw[market-intel]"

        symbol = symbol.upper()
        reddit = praw.Reddit(
            client_id=self._client_id,
            client_secret=self._client_secret,
            user_agent=self._user_agent,
        )

        subreddits = [subreddit] if subreddit else _DEFAULT_SUBREDDITS
        all_titles: list[str] = []
        post_data: list[dict] = []

        for sub_name in subreddits:
            try:
                sub = reddit.subreddit(sub_name)
                for post in sub.search(f"${symbol} OR {symbol}", limit=limit, sort="new"):
                    title = post.title
                    all_titles.append(title)
                    post_data.append({
                        "title": title,
                        "subreddit": sub_name,
                        "score": post.score,
                        "comments": post.num_comments,
                        "url": f"https://reddit.com{post.permalink}",
                    })
            except Exception:
                continue

        if not all_titles:
            return f"No Reddit mentions found for {symbol}."

        scored = score_headlines(all_titles)
        agg = aggregate_sentiment(scored)

        # Merge scored sentiment with post data
        for i, s in enumerate(scored):
            if i < len(post_data):
                post_data[i]["sentiment"] = s["sentiment"]
                post_data[i]["sentiment_score"] = s["score"]

        # Cache
        self._save_cache(symbol, agg, post_data)

        lines = [
            f"## {symbol} — Reddit Sentiment ({len(scored)} posts)",
            f"**Subreddits**: {', '.join(f'r/{s}' for s in subreddits)}",
            "",
            f"**Overall**: {agg['overall'].title()} (net score: {agg['net_score']:+.4f})",
            f"**Breakdown**: {agg['positive_count']} bullish, "
            f"{agg['negative_count']} bearish, {agg['neutral_count']} neutral",
            "",
            "### Top Posts",
        ]

        # Sort by Reddit score
        post_data.sort(key=lambda x: x.get("score", 0), reverse=True)
        for p in post_data[:10]:
            emoji = {"positive": "+", "negative": "-", "neutral": "~"}.get(p.get("sentiment", "neutral"), "~")
            lines.append(
                f"- [{emoji}] r/{p['subreddit']} ({p['score']} pts, {p['comments']} comments): "
                f"{p['title'][:100]}"
            )

        return "\n".join(lines)

    def _summary(self) -> str:
        cache_file = self._workspace / "social_sentiment_cache.json"
        if not cache_file.exists():
            return "No cached social sentiment. Run social_sentiment(action='reddit', symbol='...') first."

        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
        except Exception:
            return "Error reading social sentiment cache."

        if not data:
            return "Social sentiment cache is empty."

        lines = ["## Social Sentiment Summary", "", "| Stock | Overall | Net Score | Posts | Updated |", "|---|---|---|---|---|"]
        for sym, entry in sorted(data.items()):
            agg = entry.get("aggregate", {})
            lines.append(
                f"| {sym} | {agg.get('overall', 'N/A').title()} | "
                f"{agg.get('net_score', 0):+.4f} | {agg.get('total', 0)} | "
                f"{entry.get('updated', 'N/A')} |"
            )
        return "\n".join(lines)

    def _save_cache(self, symbol: str, aggregate: dict, posts: list) -> None:
        cache_file = self._workspace / "social_sentiment_cache.json"
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
            data[symbol] = {
                "aggregate": aggregate,
                "top_posts": posts[:5],
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
            cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass
