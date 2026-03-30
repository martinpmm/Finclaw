"""Options flow tool: options chain data and unusual activity detection."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool


class OptionsFlowTool(Tool):
    """Analyze options chain data and detect unusual options activity."""

    @property
    def name(self) -> str:
        return "options_flow"

    @property
    def description(self) -> str:
        return (
            "Analyze options chain data for a stock. View call/put chains by expiration, "
            "detect unusual activity (high volume/OI ratio, large bets), and get a summary "
            "of options market sentiment. Useful for gauging institutional conviction and "
            "pre-earnings positioning. Actions: chain, unusual, summary."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["chain", "unusual", "summary"],
                    "description": (
                        "chain: show options chain for a specific expiration; "
                        "unusual: detect unusual options activity; "
                        "summary: overview of options market sentiment"
                    ),
                },
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol",
                },
                "expiry": {
                    "type": "string",
                    "description": "Options expiration date (YYYY-MM-DD). If omitted, uses nearest expiry.",
                },
            },
            "required": ["action", "symbol"],
        }

    async def execute(self, action: str, symbol: str = "", **kwargs: Any) -> str:
        if not symbol:
            return "Error: 'symbol' is required."

        try:
            import yfinance as yf
        except ImportError:
            return "Error: yfinance not installed."

        symbol = symbol.upper()

        if action == "chain":
            return self._chain(symbol, kwargs.get("expiry", ""))
        if action == "unusual":
            return self._unusual(symbol)
        if action == "summary":
            return self._summary(symbol)
        return f"Unknown action: {action}"

    def _chain(self, symbol: str, expiry: str) -> str:
        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options

            if not expirations:
                return f"No options data available for {symbol}."

            if expiry and expiry in expirations:
                target_expiry = expiry
            else:
                target_expiry = expirations[0]

            opt = ticker.option_chain(target_expiry)
            calls = opt.calls
            puts = opt.puts

            lines = [
                f"## {symbol} Options Chain — {target_expiry}",
                "",
                f"**Available Expirations**: {', '.join(expirations[:8])}",
                "",
                "### Calls (Top 10 by Volume)",
                "| Strike | Last | Bid | Ask | Volume | OI | IV |",
                "|---|---|---|---|---|---|---|",
            ]

            top_calls = calls.nlargest(10, "volume") if "volume" in calls.columns else calls.head(10)
            for _, row in top_calls.iterrows():
                lines.append(
                    f"| ${row.get('strike', 0):.2f} | ${row.get('lastPrice', 0):.2f} | "
                    f"${row.get('bid', 0):.2f} | ${row.get('ask', 0):.2f} | "
                    f"{int(row.get('volume', 0)):,} | {int(row.get('openInterest', 0)):,} | "
                    f"{row.get('impliedVolatility', 0):.1%} |"
                )

            lines += [
                "",
                "### Puts (Top 10 by Volume)",
                "| Strike | Last | Bid | Ask | Volume | OI | IV |",
                "|---|---|---|---|---|---|---|",
            ]

            top_puts = puts.nlargest(10, "volume") if "volume" in puts.columns else puts.head(10)
            for _, row in top_puts.iterrows():
                lines.append(
                    f"| ${row.get('strike', 0):.2f} | ${row.get('lastPrice', 0):.2f} | "
                    f"${row.get('bid', 0):.2f} | ${row.get('ask', 0):.2f} | "
                    f"{int(row.get('volume', 0)):,} | {int(row.get('openInterest', 0)):,} | "
                    f"{row.get('impliedVolatility', 0):.1%} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching options chain for {symbol}: {e}"

    def _unusual(self, symbol: str) -> str:
        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                return f"No options data for {symbol}."

            unusual = []

            # Check first 3 expirations
            for exp in expirations[:3]:
                try:
                    opt = ticker.option_chain(exp)
                    for side, df in [("CALL", opt.calls), ("PUT", opt.puts)]:
                        for _, row in df.iterrows():
                            vol = row.get("volume", 0) or 0
                            oi = row.get("openInterest", 0) or 0
                            if oi > 0 and vol > 0:
                                ratio = vol / oi
                                if ratio > 3 and vol > 100:
                                    unusual.append({
                                        "expiry": exp,
                                        "type": side,
                                        "strike": row.get("strike", 0),
                                        "volume": int(vol),
                                        "oi": int(oi),
                                        "ratio": round(ratio, 1),
                                        "iv": row.get("impliedVolatility", 0),
                                        "last": row.get("lastPrice", 0),
                                    })
                except Exception:
                    continue

            if not unusual:
                return f"No unusual options activity detected for {symbol}."

            unusual.sort(key=lambda x: x["ratio"], reverse=True)

            lines = [
                f"## {symbol} — Unusual Options Activity",
                "",
                "| Expiry | Type | Strike | Volume | OI | Vol/OI | IV | Last |",
                "|---|---|---|---|---|---|---|---|",
            ]
            for u in unusual[:15]:
                lines.append(
                    f"| {u['expiry']} | {u['type']} | ${u['strike']:.2f} | "
                    f"{u['volume']:,} | {u['oi']:,} | {u['ratio']}x | "
                    f"{u['iv']:.1%} | ${u['last']:.2f} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"Error detecting unusual options for {symbol}: {e}"

    def _summary(self, symbol: str) -> str:
        import yfinance as yf

        try:
            ticker = yf.Ticker(symbol)
            expirations = ticker.options
            if not expirations:
                return f"No options data for {symbol}."

            total_call_vol = 0
            total_put_vol = 0
            total_call_oi = 0
            total_put_oi = 0

            # Aggregate across first 4 expirations
            for exp in expirations[:4]:
                try:
                    opt = ticker.option_chain(exp)
                    total_call_vol += opt.calls["volume"].sum() if "volume" in opt.calls else 0
                    total_put_vol += opt.puts["volume"].sum() if "volume" in opt.puts else 0
                    total_call_oi += opt.calls["openInterest"].sum() if "openInterest" in opt.calls else 0
                    total_put_oi += opt.puts["openInterest"].sum() if "openInterest" in opt.puts else 0
                except Exception:
                    continue

            pc_ratio_vol = total_put_vol / total_call_vol if total_call_vol > 0 else 0
            pc_ratio_oi = total_put_oi / total_call_oi if total_call_oi > 0 else 0

            if pc_ratio_vol < 0.7:
                sentiment = "Bullish (low put/call ratio)"
            elif pc_ratio_vol > 1.0:
                sentiment = "Bearish (high put/call ratio)"
            else:
                sentiment = "Neutral"

            lines = [
                f"## {symbol} — Options Summary",
                "",
                f"**Sentiment**: {sentiment}",
                f"**Expirations analyzed**: {', '.join(expirations[:4])}",
                "",
                "### Volume",
                f"- Call volume: {int(total_call_vol):,}",
                f"- Put volume: {int(total_put_vol):,}",
                f"- Put/Call ratio (volume): {pc_ratio_vol:.2f}",
                "",
                "### Open Interest",
                f"- Call OI: {int(total_call_oi):,}",
                f"- Put OI: {int(total_put_oi):,}",
                f"- Put/Call ratio (OI): {pc_ratio_oi:.2f}",
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching options summary for {symbol}: {e}"
