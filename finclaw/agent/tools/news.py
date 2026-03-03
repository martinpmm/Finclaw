"""News tools: stock-specific and global market news."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from finclaw.agent.tools.base import Tool


def _parse_news_item(item: dict) -> tuple[str, str, str, str]:
    """Parse a yfinance news item, handling both old and new API formats.

    Returns (title, publisher, link, age_str).
    """
    # New format: item["content"] dict with nested fields
    content = item.get("content", {})
    if content:
        title = content.get("title", "No title")
        publisher = (content.get("provider") or {}).get("displayName", "Unknown")
        link = (content.get("canonicalUrl") or {}).get("url", "")
        pub_date_str = content.get("pubDate") or content.get("displayTime", "")
        if pub_date_str:
            try:
                dt = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                now = datetime.now(tz=timezone.utc)
                age = now - dt
                if age.days > 0:
                    age_str = f"{age.days}d ago"
                elif age.seconds > 3600:
                    age_str = f"{age.seconds // 3600}h ago"
                else:
                    age_str = f"{age.seconds // 60}m ago"
            except (ValueError, TypeError):
                age_str = ""
        else:
            age_str = ""
    else:
        # Legacy format: flat dict
        title = item.get("title", "No title")
        publisher = item.get("publisher", "Unknown")
        link = item.get("link", "")
        ts = item.get("providerPublishTime")
        if ts:
            dt = datetime.fromtimestamp(ts)
            age = datetime.now() - dt
            if age.days > 0:
                age_str = f"{age.days}d ago"
            elif age.seconds > 3600:
                age_str = f"{age.seconds // 3600}h ago"
            else:
                age_str = f"{age.seconds // 60}m ago"
        else:
            age_str = ""
    return title, publisher, link, age_str


class StockNewsTool(Tool):
    """Get recent news for a specific stock."""

    @property
    def name(self) -> str:
        return "stock_news"

    @property
    def description(self) -> str:
        return (
            "Get recent news articles for a specific stock. "
            "Returns headlines, sources, and summaries. "
            "Use this to check for earnings reports, product launches, analyst upgrades, regulatory news, etc."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of news items to return (default: 10, max: 20)",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, limit: int = 10, **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            news = ticker.news

            if not news:
                return f"No recent news found for {symbol}."

            news = news[:limit]
            lines = [f"## {symbol.upper()} — Recent News ({len(news)} articles)", ""]

            for item in news:
                title, publisher, link, age_str = _parse_news_item(item)
                lines.append(f"**{title}**")
                lines.append(f"  *{publisher}* · {age_str}")
                if link:
                    lines.append(f"  {link}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching news for {symbol}: {e}"


class MarketNewsTool(Tool):
    """Get general market and macroeconomic news."""

    @property
    def name(self) -> str:
        return "market_news"

    @property
    def description(self) -> str:
        return (
            "Get general market and macroeconomic news: Fed decisions, economic data, "
            "sector trends, and broad market developments. "
            "Use this for macro context when analyzing stocks or market conditions."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of news items to return (default: 10)",
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": [],
        }

    async def execute(self, limit: int = 10, **kwargs: Any) -> str:
        # Use broad market ETFs / indices as proxies for market news
        market_symbols = ["SPY", "QQQ", "^VIX"]

        try:
            import yfinance as yf

            all_news: list[dict] = []
            seen_titles: set[str] = set()

            for sym in market_symbols:
                try:
                    ticker = yf.Ticker(sym)
                    news = ticker.news or []
                    for item in news:
                        title = (item.get("content") or {}).get("title") or item.get("title", "")
                        if title and title not in seen_titles:
                            seen_titles.add(title)
                            all_news.append(item)
                except Exception:
                    continue

            # Sort by publish time (most recent first) — handle both old and new formats
            def _sort_key(x: dict) -> str:
                content = x.get("content", {})
                return content.get("pubDate") or content.get("displayTime") or str(x.get("providerPublishTime", "0"))

            all_news.sort(key=_sort_key, reverse=True)
            all_news = all_news[:limit]

            if not all_news:
                return "No market news available at this time."

            lines = [f"## Market News ({len(all_news)} articles)", ""]

            for item in all_news:
                title, publisher, link, age_str = _parse_news_item(item)
                lines.append(f"**{title}**")
                lines.append(f"  *{publisher}* · {age_str}")
                if link:
                    lines.append(f"  {link}")
                lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching market news: {e}"
