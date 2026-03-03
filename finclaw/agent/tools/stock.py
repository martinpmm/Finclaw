"""Stock price tools using yfinance."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool


class StockQuoteTool(Tool):
    """Get current stock quote: price, change, volume, market cap, 52-week range."""

    @property
    def name(self) -> str:
        return "stock_quote"

    @property
    def description(self) -> str:
        return (
            "Get the current quote for a stock or ETF: price, day change, volume, "
            "market cap, P/E ratio, and 52-week range. Use this for real-time price checks."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL, NVDA, SPY, BTC-USD)",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            info = ticker.info

            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
            prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
            day_change = ((price - prev_close) / prev_close * 100) if price and prev_close else None
            day_high = info.get("dayHigh") or info.get("regularMarketDayHigh")
            day_low = info.get("dayLow") or info.get("regularMarketDayLow")
            volume = info.get("volume") or info.get("regularMarketVolume")
            avg_volume = info.get("averageVolume")
            market_cap = info.get("marketCap")
            pe_ratio = info.get("trailingPE")
            week_52_high = info.get("fiftyTwoWeekHigh")
            week_52_low = info.get("fiftyTwoWeekLow")
            name = info.get("longName") or info.get("shortName") or symbol.upper()

            lines = [f"## {name} ({symbol.upper()})"]
            if price:
                change_str = f" ({day_change:+.2f}%)" if day_change is not None else ""
                lines.append(f"**Price**: ${price:.2f}{change_str}")
            if prev_close:
                lines.append(f"**Previous Close**: ${prev_close:.2f}")
            if day_high and day_low:
                lines.append(f"**Day Range**: ${day_low:.2f} – ${day_high:.2f}")
            if week_52_high and week_52_low:
                lines.append(f"**52-Week Range**: ${week_52_low:.2f} – ${week_52_high:.2f}")
            if volume:
                vol_str = f"{volume:,}"
                avg_str = f" (avg {avg_volume:,})" if avg_volume else ""
                lines.append(f"**Volume**: {vol_str}{avg_str}")
            if market_cap:
                if market_cap >= 1e12:
                    cap_str = f"${market_cap/1e12:.2f}T"
                elif market_cap >= 1e9:
                    cap_str = f"${market_cap/1e9:.2f}B"
                else:
                    cap_str = f"${market_cap/1e6:.2f}M"
                lines.append(f"**Market Cap**: {cap_str}")
            if pe_ratio:
                lines.append(f"**P/E (TTM)**: {pe_ratio:.1f}x")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching quote for {symbol}: {e}"


class StockHistoryTool(Tool):
    """Get historical OHLCV price data for a stock."""

    @property
    def name(self) -> str:
        return "stock_history"

    @property
    def description(self) -> str:
        return (
            "Get historical OHLCV (Open, High, Low, Close, Volume) price data for a stock. "
            "Useful for analyzing price trends and performance over time."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g. AAPL, NVDA)",
                },
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
                    "description": "Time period for historical data. Default is 1mo.",
                },
            },
            "required": ["symbol"],
        }

    async def execute(self, symbol: str, period: str = "1mo", **kwargs: Any) -> str:
        try:
            import yfinance as yf

            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period=period)

            if hist.empty:
                return f"No historical data found for {symbol}."

            # Summary stats
            start_price = hist["Close"].iloc[0]
            end_price = hist["Close"].iloc[-1]
            pct_change = (end_price - start_price) / start_price * 100
            high = hist["High"].max()
            low = hist["Low"].min()

            lines = [
                f"## {symbol.upper()} — Historical Data ({period})",
                f"**Period Return**: {pct_change:+.2f}%",
                f"**Start**: ${start_price:.2f}  →  **End**: ${end_price:.2f}",
                f"**Period High**: ${high:.2f}  |  **Period Low**: ${low:.2f}",
                "",
                "**Recent prices** (last 10 trading days):",
                "Date | Close | Change",
                "---|---|---",
            ]

            recent = hist.tail(10)
            for i, (date, row) in enumerate(recent.iterrows()):
                prev_close = recent["Close"].iloc[i - 1] if i > 0 else row["Close"]
                chg = (row["Close"] - prev_close) / prev_close * 100 if i > 0 else 0
                date_str = date.strftime("%Y-%m-%d")
                lines.append(f"{date_str} | ${row['Close']:.2f} | {chg:+.2f}%")

            return "\n".join(lines)

        except Exception as e:
            return f"Error fetching history for {symbol}: {e}"
