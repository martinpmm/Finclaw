"""Technical indicators tool using yfinance + stockstats."""

from __future__ import annotations

from typing import Any

from finclaw.agent.tools.base import Tool

# Best parameter windows adapted from TradingAgents dataflows/y_finance.py
_INDICATOR_PARAMS: dict[str, dict] = {
    "close_50_sma": {"look_back_days": 60, "description": "50-day Simple Moving Average"},
    "close_200_sma": {"look_back_days": 210, "description": "200-day Simple Moving Average"},
    "close_10_ema": {"look_back_days": 20, "description": "10-day Exponential Moving Average"},
    "macd": {"look_back_days": 60, "description": "MACD line (12/26 EMA difference)"},
    "macds": {"look_back_days": 60, "description": "MACD Signal line (9-day EMA of MACD)"},
    "macdh": {"look_back_days": 60, "description": "MACD Histogram (MACD - Signal)"},
    "rsi": {"look_back_days": 20, "description": "Relative Strength Index (14-day)"},
    "boll": {"look_back_days": 30, "description": "Bollinger Band middle (20-day SMA)"},
    "boll_ub": {"look_back_days": 30, "description": "Bollinger Band upper (SMA + 2σ)"},
    "boll_lb": {"look_back_days": 30, "description": "Bollinger Band lower (SMA - 2σ)"},
    "atr": {"look_back_days": 20, "description": "Average True Range (14-day volatility)"},
    "vwma": {"look_back_days": 20, "description": "Volume-Weighted Moving Average (14-day)"},
    "mfi": {"look_back_days": 20, "description": "Money Flow Index (14-day)"},
}


class TechnicalIndicatorsTool(Tool):
    """Calculate technical indicators for a stock."""

    @property
    def name(self) -> str:
        return "technical_indicators"

    @property
    def description(self) -> str:
        return (
            "Calculate technical indicators for a stock: RSI, MACD, Bollinger Bands, "
            "Moving Averages (SMA/EMA), ATR, VWMA, MFI. "
            "Returns the most recent values with brief interpretation."
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
                "indicators": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": list(_INDICATOR_PARAMS.keys()),
                    },
                    "description": (
                        "List of indicators to calculate. "
                        "Options: rsi, macd, macds, macdh, boll, boll_ub, boll_lb, "
                        "atr, vwma, mfi, close_50_sma, close_200_sma, close_10_ema. "
                        "If omitted, returns RSI, MACD, and Bollinger Bands."
                    ),
                },
            },
            "required": ["symbol"],
        }

    async def execute(
        self,
        symbol: str,
        indicators: list[str] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            import yfinance as yf
            from stockstats import StockDataFrame

            if not indicators:
                indicators = ["rsi", "macd", "macds", "macdh", "boll", "boll_ub", "boll_lb"]

            # Determine the lookback needed (use the max across requested indicators)
            look_back = max(
                _INDICATOR_PARAMS.get(ind, {}).get("look_back_days", 30) for ind in indicators
            )
            # Add buffer for indicator calculation warmup
            fetch_days = look_back + 60

            ticker = yf.Ticker(symbol.upper())
            hist = ticker.history(period=f"{min(fetch_days, 365)}d")

            if hist.empty or len(hist) < 5:
                return f"Insufficient price data for {symbol}."

            # Prepare for stockstats (requires lowercase columns)
            hist = hist.rename(columns={
                "Open": "open", "High": "high", "Low": "low",
                "Close": "close", "Volume": "volume",
            })
            sdf = StockDataFrame.retype(hist.copy())

            lines = [f"## {symbol.upper()} — Technical Indicators", ""]
            current_price = hist["close"].iloc[-1]
            lines.append(f"**Current Price**: ${current_price:.2f}")
            lines.append("")

            results = []
            for ind in indicators:
                try:
                    col_data = sdf[ind]
                    val = col_data.iloc[-1]
                    desc = _INDICATOR_PARAMS.get(ind, {}).get("description", ind)
                    interpretation = _interpret(ind, val, current_price, hist)
                    if isinstance(val, float):
                        val_str = f"{val:.2f}"
                    else:
                        val_str = str(val)
                    results.append(f"- **{desc}** ({ind}): {val_str}{interpretation}")
                except Exception:
                    results.append(f"- **{ind}**: Could not calculate")

            lines.extend(results)
            return "\n".join(lines)

        except ImportError:
            return "Error: stockstats is required. Install with: pip install stockstats"
        except Exception as e:
            return f"Error calculating indicators for {symbol}: {e}"


def _interpret(indicator: str, val: float, price: float, hist: Any) -> str:
    """Return a brief interpretation string for the indicator value."""
    try:
        if indicator == "rsi":
            if val >= 70:
                return " ⚠️ Overbought"
            if val <= 30:
                return " 📉 Oversold"
            return " (neutral)"
        if indicator == "macdh":
            if val > 0:
                return " (bullish momentum)"
            if val < 0:
                return " (bearish momentum)"
        if indicator == "boll_ub":
            if price >= val * 0.99:
                return " ⚠️ Price near upper band"
        if indicator == "boll_lb":
            if price <= val * 1.01:
                return " 📉 Price near lower band"
        if indicator == "close_50_sma":
            if price > val:
                return " (price above — bullish)"
            return " (price below — bearish)"
        if indicator == "close_200_sma":
            if price > val:
                return " (price above — long-term uptrend)"
            return " (price below — long-term downtrend)"
        if indicator == "mfi":
            if val >= 80:
                return " ⚠️ Overbought"
            if val <= 20:
                return " 📉 Oversold"
    except Exception:
        pass
    return ""
