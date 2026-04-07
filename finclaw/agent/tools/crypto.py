"""Crypto tool: cryptocurrency quotes, history, and exchange data via ccxt."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool


class CryptoTool(Tool):
    """Get cryptocurrency market data from major exchanges."""

    @property
    def name(self) -> str:
        return "crypto"

    @property
    def description(self) -> str:
        return (
            "Get cryptocurrency market data: real-time quotes, price history, and exchange info. "
            "Supports 100+ exchanges via ccxt (Binance, Coinbase, Kraken, etc.). "
            "Use for BTC, ETH, SOL, and any trading pair. "
            "Actions: quote, history, exchanges."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["quote", "history", "exchanges"],
                    "description": (
                        "quote: current price and 24h stats; "
                        "history: OHLCV candle history; "
                        "exchanges: list available exchanges"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Trading pair (e.g. BTC/USDT, ETH/USD). Default: BTC/USDT.",
                },
                "exchange": {
                    "type": "string",
                    "description": "Exchange name (e.g. binance, coinbase, kraken). Default: binance.",
                },
                "period": {
                    "type": "string",
                    "enum": ["1h", "4h", "1d", "1w"],
                    "description": "Candle timeframe for history. Default: 1d.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of candles for history. Default: 30.",
                    "minimum": 1,
                    "maximum": 200,
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        try:
            import ccxt
        except ImportError:
            return "Error: ccxt not installed. Install with: pip install finclaw[multi-asset]"

        if action == "quote":
            return self._quote(kwargs.get("symbol", "BTC/USDT"), kwargs.get("exchange", "binance"))
        if action == "history":
            return self._history(
                kwargs.get("symbol", "BTC/USDT"),
                kwargs.get("exchange", "binance"),
                kwargs.get("period", "1d"),
                kwargs.get("limit", 30),
            )
        if action == "exchanges":
            return self._exchanges()
        return f"Unknown action: {action}"

    def _quote(self, symbol: str, exchange_name: str) -> str:
        import ccxt

        try:
            exchange_cls = getattr(ccxt, exchange_name.lower(), None)
            if not exchange_cls:
                return f"Exchange '{exchange_name}' not found. Use action='exchanges' to list available."

            exchange = exchange_cls()
            ticker = exchange.fetch_ticker(symbol)

            lines = [
                f"## {symbol} on {exchange_name.title()}",
                "",
                f"- **Last Price**: ${ticker.get('last', 0):,.2f}",
                f"- **24h Change**: {ticker.get('percentage', 0):+.2f}%",
                f"- **24h High**: ${ticker.get('high', 0):,.2f}",
                f"- **24h Low**: ${ticker.get('low', 0):,.2f}",
                f"- **24h Volume**: {ticker.get('baseVolume', 0):,.2f}",
                f"- **24h Quote Volume**: ${ticker.get('quoteVolume', 0):,.0f}",
                f"- **Bid**: ${ticker.get('bid', 0):,.2f}",
                f"- **Ask**: ${ticker.get('ask', 0):,.2f}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching {symbol} from {exchange_name}: {e}"

    def _history(self, symbol: str, exchange_name: str, period: str, limit: int) -> str:
        import ccxt

        try:
            exchange_cls = getattr(ccxt, exchange_name.lower(), None)
            if not exchange_cls:
                return f"Exchange '{exchange_name}' not found."

            exchange = exchange_cls()
            timeframe_map = {"1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w"}
            tf = timeframe_map.get(period, "1d")

            ohlcv = exchange.fetch_ohlcv(symbol, timeframe=tf, limit=limit)
            if not ohlcv:
                return f"No history data for {symbol}."

            from datetime import datetime

            lines = [
                f"## {symbol} — {period} Candles ({exchange_name.title()})",
                "",
                "| Date | Open | High | Low | Close | Volume |",
                "|---|---|---|---|---|---|",
            ]

            for candle in ohlcv:
                ts, o, h, l, c, v = candle
                dt = datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M")
                lines.append(f"| {dt} | ${o:,.2f} | ${h:,.2f} | ${l:,.2f} | ${c:,.2f} | {v:,.2f} |")

            # Performance
            if len(ohlcv) >= 2:
                first_close = ohlcv[0][4]
                last_close = ohlcv[-1][4]
                change = (last_close - first_close) / first_close * 100
                lines.append(f"\n**Period Return**: {change:+.2f}%")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching history for {symbol}: {e}"

    def _exchanges(self) -> str:
        import ccxt

        popular = ["binance", "coinbase", "kraken", "bybit", "okx", "kucoin", "bitfinex", "gate"]
        lines = [
            "## Available Crypto Exchanges",
            "",
            "### Popular Exchanges",
        ]
        for name in popular:
            if hasattr(ccxt, name):
                lines.append(f"- **{name}**")

        lines += [
            "",
            f"**Total exchanges supported**: {len(ccxt.exchanges)}",
            "",
            "Use `crypto(action='quote', symbol='BTC/USDT', exchange='binance')` to get a quote.",
        ]
        return "\n".join(lines)
