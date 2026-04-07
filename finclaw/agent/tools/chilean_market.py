"""Chilean market tool: CLP/USD, IPSA, and USDC arbitrage signals."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool


class ChileanMarketTool(Tool):
    """Access Chilean financial market data: CLP/USD, IPSA index, and crypto arbitrage."""

    @property
    def name(self) -> str:
        return "chilean_market"

    @property
    def description(self) -> str:
        return (
            "Access Chilean financial market data. Get CLP/USD exchange rate from multiple "
            "sources, IPSA index performance, and USDC/CLP vs USD/CLP spread for arbitrage "
            "signal detection. Uses Buda.com API and public CMF data. "
            "Actions: usd_clp, ipsa, arbitrage."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["usd_clp", "ipsa", "arbitrage"],
                    "description": (
                        "usd_clp: current USD/CLP exchange rate; "
                        "ipsa: IPSA index components and performance; "
                        "arbitrage: USDC/CLP vs USD/CLP spread"
                    ),
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        if action == "usd_clp":
            return await self._usd_clp()
        if action == "ipsa":
            return await self._ipsa()
        if action == "arbitrage":
            return await self._arbitrage()
        return f"Unknown action: {action}"

    async def _usd_clp(self) -> str:
        import httpx

        lines = ["## USD/CLP Exchange Rate", ""]

        # Buda.com API (public, no auth)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://www.buda.com/api/v2/markets/usdc-clp/ticker")
                if resp.status_code == 200:
                    data = resp.json()
                    ticker = data.get("ticker", {})
                    last = ticker.get("last_price", [])
                    vol = ticker.get("volume", [])
                    lines.append(f"**Buda.com (USDC/CLP)**: ${last[0] if last else 'N/A'} CLP")
                    lines.append(f"  Volume: {vol[0] if vol else 'N/A'} USDC")
        except Exception:
            lines.append("Buda.com: unavailable")

        # yfinance for official rate
        try:
            import yfinance as yf
            ticker = yf.Ticker("CLP=X")
            info = ticker.info
            rate = info.get("regularMarketPrice", 0)
            if rate:
                # CLP=X gives USD per CLP, we want CLP per USD
                clp_per_usd = 1 / rate if rate > 0 else 0
                lines.append(f"**Market Rate (CLP=X)**: ${clp_per_usd:.2f} CLP/USD")
        except Exception:
            pass

        return "\n".join(lines)

    async def _ipsa(self) -> str:
        try:
            import yfinance as yf

            # IPSA ETF proxy or direct index
            ticker = yf.Ticker("^IPSA")
            hist = ticker.history(period="1mo")

            if hist.empty:
                return "IPSA index data not available via yfinance. Try web_search for current IPSA data."

            last_close = hist["Close"].iloc[-1]
            first_close = hist["Close"].iloc[0]
            change = (last_close - first_close) / first_close * 100

            lines = [
                "## IPSA Index (Santiago Stock Exchange)",
                "",
                f"**Current Level**: {last_close:,.2f}",
                f"**1-Month Return**: {change:+.2f}%",
                "",
                "### Recent History",
                "| Date | Close | Change |",
                "|---|---|---|",
            ]

            for i in range(-min(10, len(hist)), 0):
                row = hist.iloc[i]
                dt = hist.index[i].strftime("%Y-%m-%d")
                close = row["Close"]
                prev = hist["Close"].iloc[i - 1] if abs(i) < len(hist) else close
                day_chg = (close - prev) / prev * 100 if prev > 0 else 0
                lines.append(f"| {dt} | {close:,.2f} | {day_chg:+.2f}% |")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching IPSA data: {e}"

    async def _arbitrage(self) -> str:
        import httpx

        lines = ["## USDC/CLP Arbitrage Signal", ""]

        buda_rate = None
        market_rate = None

        # Get Buda USDC/CLP rate
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get("https://www.buda.com/api/v2/markets/usdc-clp/ticker")
                if resp.status_code == 200:
                    data = resp.json()
                    last = data.get("ticker", {}).get("last_price", [])
                    if last:
                        buda_rate = float(last[0])
                        lines.append(f"**Buda USDC/CLP**: ${buda_rate:.2f}")
        except Exception:
            pass

        # Get market USD/CLP
        try:
            import yfinance as yf
            ticker = yf.Ticker("CLP=X")
            info = ticker.info
            rate = info.get("regularMarketPrice", 0)
            if rate and rate > 0:
                market_rate = 1 / rate
                lines.append(f"**Market USD/CLP**: ${market_rate:.2f}")
        except Exception:
            pass

        if buda_rate and market_rate:
            spread = buda_rate - market_rate
            spread_pct = (spread / market_rate) * 100
            lines += [
                "",
                f"**Spread**: ${spread:.2f} ({spread_pct:+.2f}%)",
                "",
            ]
            if abs(spread_pct) > 1.5:
                direction = "USDC premium on Buda" if spread_pct > 0 else "USDC discount on Buda"
                lines.append(f"**Signal**: Significant spread detected — {direction}")
                lines.append("Consider arbitrage opportunity if spread exceeds transaction costs.")
            else:
                lines.append("**Signal**: Spread within normal range. No arbitrage opportunity.")
        else:
            lines.append("\nCould not calculate arbitrage spread — missing rate data.")

        return "\n".join(lines)
