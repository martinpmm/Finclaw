"""Portfolio tracker tool: positions, P&L, optimization, backtesting, tearsheets."""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool

_HEADER = """\
# Portfolio

Finclaw portfolio tracker — positions, performance, and analytics.

<!-- Positions will appear below as you add them -->
"""


class PortfolioTool(Tool):
    """Manage and analyze an investment portfolio."""

    def __init__(self, workspace: Path) -> None:
        self._workspace = workspace
        self._file = workspace / "PORTFOLIO.md"

    @property
    def name(self) -> str:
        return "portfolio"

    @property
    def description(self) -> str:
        return (
            "Manage and analyze an investment portfolio. Add/remove positions with cost basis, "
            "view current P&L and allocation, run portfolio optimization (efficient frontier, "
            "Black-Litterman, HRP), backtest strategies, and generate performance tearsheets "
            "(Sharpe, Sortino, max drawdown, rolling beta). "
            "Actions: add_position, remove_position, update_position, list, summary, "
            "analyze, optimize, backtest, tearsheet."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "add_position", "remove_position", "update_position",
                        "list", "summary", "analyze", "optimize", "backtest", "tearsheet",
                    ],
                },
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "shares": {"type": "number", "description": "Number of shares"},
                "cost_basis": {"type": "number", "description": "Cost per share in USD"},
                "date": {"type": "string", "description": "Purchase date (YYYY-MM-DD)"},
                "strategy": {
                    "type": "string",
                    "enum": ["efficient_frontier", "black_litterman", "hrp", "cvar"],
                    "description": "Optimization strategy. Default: efficient_frontier.",
                },
                "period": {
                    "type": "string",
                    "enum": ["6mo", "1y", "2y", "3y", "5y"],
                    "description": "Lookback period for analysis/backtest. Default: 1y.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        if action == "add_position":
            return self._add_position(
                kwargs.get("symbol", ""), kwargs.get("shares", 0),
                kwargs.get("cost_basis", 0), kwargs.get("date", ""),
            )
        if action == "remove_position":
            return self._remove_position(kwargs.get("symbol", ""))
        if action == "update_position":
            return self._add_position(
                kwargs.get("symbol", ""), kwargs.get("shares", 0),
                kwargs.get("cost_basis", 0), kwargs.get("date", ""),
            )
        if action == "list":
            return self._list()
        if action == "summary":
            return await self._summary()
        if action == "analyze":
            return await self._analyze(kwargs.get("period", "1y"))
        if action == "optimize":
            return await self._optimize(kwargs.get("strategy", "efficient_frontier"), kwargs.get("period", "1y"))
        if action == "backtest":
            return await self._backtest(kwargs.get("period", "1y"))
        if action == "tearsheet":
            return await self._tearsheet(kwargs.get("period", "1y"))
        return f"Unknown action: {action}"

    # --- CRUD ---

    def _add_position(self, symbol: str, shares: float, cost_basis: float, dt: str) -> str:
        if not symbol:
            return "Error: 'symbol' is required."
        if shares <= 0:
            return "Error: 'shares' must be positive."
        if cost_basis <= 0:
            return "Error: 'cost_basis' must be positive."

        symbol = symbol.upper()
        if not dt:
            dt = date.today().isoformat()

        content = self._read()
        # Remove existing if present
        content = self._remove_section(content, symbol)

        entry = (
            f"\n## {symbol}\n"
            f"- **Shares**: {shares}\n"
            f"- **Cost Basis**: ${cost_basis:.2f}\n"
            f"- **Date**: {dt}\n"
            f"- **Total Cost**: ${shares * cost_basis:,.2f}\n"
            f"\n---\n"
        )
        content = content.rstrip("\n") + "\n" + entry
        self._write(content)
        return f"Added {shares} shares of {symbol} at ${cost_basis:.2f}/share to portfolio."

    def _remove_position(self, symbol: str) -> str:
        if not symbol:
            return "Error: 'symbol' is required."
        symbol = symbol.upper()
        content = self._read()
        new_content = self._remove_section(content, symbol)
        if new_content == content:
            return f"No position found for {symbol}."
        self._write(new_content)
        return f"Removed {symbol} from portfolio."

    def _list(self) -> str:
        positions = self._parse_positions()
        if not positions:
            return "Portfolio is empty. Use portfolio(action='add_position') to add holdings."

        lines = ["## Portfolio Positions", "", "| Symbol | Shares | Cost Basis | Date | Total Cost |", "|---|---|---|---|---|"]
        for p in positions:
            total = p["shares"] * p["cost_basis"]
            lines.append(
                f"| {p['symbol']} | {p['shares']} | ${p['cost_basis']:.2f} | {p['date']} | ${total:,.2f} |"
            )
        return "\n".join(lines)

    # --- Analysis ---

    async def _summary(self) -> str:
        positions = self._parse_positions()
        if not positions:
            return "Portfolio is empty."

        try:
            import yfinance as yf
        except ImportError:
            return "Error: yfinance not installed."

        lines = ["## Portfolio Summary", "", "| Symbol | Shares | Cost | Current | Value | P&L | P&L % |", "|---|---|---|---|---|---|---|"]
        total_cost = 0.0
        total_value = 0.0

        for p in positions:
            try:
                ticker = yf.Ticker(p["symbol"])
                price = ticker.info.get("currentPrice") or ticker.info.get("regularMarketPrice", 0)
                cost = p["shares"] * p["cost_basis"]
                value = p["shares"] * price
                pnl = value - cost
                pnl_pct = (pnl / cost * 100) if cost > 0 else 0
                total_cost += cost
                total_value += value
                lines.append(
                    f"| {p['symbol']} | {p['shares']} | ${p['cost_basis']:.2f} | "
                    f"${price:.2f} | ${value:,.2f} | ${pnl:+,.2f} | {pnl_pct:+.1f}% |"
                )
            except Exception:
                lines.append(f"| {p['symbol']} | {p['shares']} | ${p['cost_basis']:.2f} | N/A | N/A | N/A | N/A |")

        total_pnl = total_value - total_cost
        total_pnl_pct = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        lines += [
            "",
            f"**Total Cost**: ${total_cost:,.2f}",
            f"**Total Value**: ${total_value:,.2f}",
            f"**Total P&L**: ${total_pnl:+,.2f} ({total_pnl_pct:+.1f}%)",
        ]

        # Allocation
        if total_value > 0:
            lines += ["", "### Allocation"]
            for p in positions:
                try:
                    ticker = yf.Ticker(p["symbol"])
                    price = ticker.info.get("currentPrice") or ticker.info.get("regularMarketPrice", 0)
                    value = p["shares"] * price
                    weight = value / total_value * 100
                    lines.append(f"- {p['symbol']}: {weight:.1f}%")
                except Exception:
                    pass

        return "\n".join(lines)

    async def _analyze(self, period: str) -> str:
        positions = self._parse_positions()
        if not positions:
            return "Portfolio is empty."

        try:
            import quantstats as qs
            import yfinance as yf
            import pandas as pd
        except ImportError:
            return "Error: quantstats not installed. Install with: pip install finclaw[portfolio]"

        symbols = [p["symbol"] for p in positions]
        weights = self._get_equal_weights(positions)

        # Download price history
        data = yf.download(symbols, period=period, progress=False)["Close"]
        if data.empty:
            return "Could not fetch price data."

        # Create portfolio returns
        returns = data.pct_change().dropna()
        if isinstance(returns, pd.Series):
            port_returns = returns
        else:
            port_returns = (returns * list(weights.values())).sum(axis=1)

        # Compute metrics
        sharpe = qs.stats.sharpe(port_returns)
        sortino = qs.stats.sortino(port_returns)
        max_dd = qs.stats.max_drawdown(port_returns)
        volatility = qs.stats.volatility(port_returns)
        cagr = qs.stats.cagr(port_returns)

        lines = [
            f"## Portfolio Analysis ({period})",
            "",
            f"- **CAGR**: {cagr * 100:.2f}%",
            f"- **Sharpe Ratio**: {sharpe:.2f}",
            f"- **Sortino Ratio**: {sortino:.2f}",
            f"- **Max Drawdown**: {max_dd * 100:.2f}%",
            f"- **Volatility**: {volatility * 100:.2f}%",
        ]
        return "\n".join(lines)

    async def _optimize(self, strategy: str, period: str) -> str:
        positions = self._parse_positions()
        if not positions:
            return "Portfolio is empty."

        try:
            from pypfopt import EfficientFrontier, HRPOpt, risk_models, expected_returns
            import yfinance as yf
        except ImportError:
            return "Error: PyPortfolioOpt not installed. Install with: pip install finclaw[portfolio]"

        symbols = [p["symbol"] for p in positions]
        data = yf.download(symbols, period=period, progress=False)["Close"]
        if data.empty:
            return "Could not fetch price data."

        mu = expected_returns.mean_historical_return(data)
        S = risk_models.sample_cov(data)

        if strategy == "hrp":
            returns = data.pct_change().dropna()
            opt = HRPOpt(returns)
            weights = opt.optimize()
        else:
            ef = EfficientFrontier(mu, S)
            if strategy == "efficient_frontier":
                weights = ef.max_sharpe()
            elif strategy == "black_litterman":
                weights = ef.min_volatility()
            else:
                weights = ef.max_sharpe()
            weights = dict(weights)

        lines = [
            f"## Portfolio Optimization ({strategy.replace('_', ' ').title()})",
            "",
            "### Recommended Weights",
            "| Symbol | Current Weight | Optimal Weight | Action |",
            "|---|---|---|---|",
        ]

        current_weights = self._get_equal_weights(positions)
        for sym in symbols:
            cw = current_weights.get(sym, 0) * 100
            ow = weights.get(sym, 0) * 100
            diff = ow - cw
            action = "increase" if diff > 2 else "decrease" if diff < -2 else "hold"
            lines.append(f"| {sym} | {cw:.1f}% | {ow:.1f}% | {action} |")

        return "\n".join(lines)

    async def _backtest(self, period: str) -> str:
        positions = self._parse_positions()
        if not positions:
            return "Portfolio is empty."

        try:
            import vectorbt as vbt
        except ImportError:
            return "Error: vectorbt not installed. Install with: pip install finclaw[portfolio]"

        try:
            import yfinance as yf
            symbols = [p["symbol"] for p in positions]
            data = yf.download(symbols, period=period, progress=False)["Close"]
            if data.empty:
                return "Could not fetch price data."

            # Equal-weight backtest
            pf = vbt.Portfolio.from_holding(data, init_cash=100000)
            stats = pf.stats()

            lines = [
                f"## Backtest Results ({period}, equal-weight)",
                "",
                str(stats),
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error running backtest: {e}"

    async def _tearsheet(self, period: str) -> str:
        positions = self._parse_positions()
        if not positions:
            return "Portfolio is empty."

        try:
            import quantstats as qs
            import yfinance as yf
            import pandas as pd
        except ImportError:
            return "Error: quantstats not installed. Install with: pip install finclaw[portfolio]"

        symbols = [p["symbol"] for p in positions]
        weights = self._get_equal_weights(positions)

        data = yf.download(symbols, period=period, progress=False)["Close"]
        if data.empty:
            return "Could not fetch price data."

        returns = data.pct_change().dropna()
        if isinstance(returns, pd.Series):
            port_returns = returns
        else:
            port_returns = (returns * list(weights.values())).sum(axis=1)

        # Generate text-based tearsheet
        sharpe = qs.stats.sharpe(port_returns)
        sortino = qs.stats.sortino(port_returns)
        max_dd = qs.stats.max_drawdown(port_returns)
        cagr = qs.stats.cagr(port_returns)
        volatility = qs.stats.volatility(port_returns)
        calmar = qs.stats.calmar(port_returns)
        win_rate = qs.stats.win_rate(port_returns)
        best_day = port_returns.max()
        worst_day = port_returns.min()
        avg_return = port_returns.mean()

        lines = [
            f"## Portfolio Tearsheet ({period})",
            "",
            "### Performance Metrics",
            f"- **CAGR**: {cagr * 100:.2f}%",
            f"- **Sharpe Ratio**: {sharpe:.2f}",
            f"- **Sortino Ratio**: {sortino:.2f}",
            f"- **Calmar Ratio**: {calmar:.2f}",
            f"- **Max Drawdown**: {max_dd * 100:.2f}%",
            f"- **Volatility (ann.)**: {volatility * 100:.2f}%",
            "",
            "### Daily Return Stats",
            f"- **Avg Daily Return**: {avg_return * 100:.4f}%",
            f"- **Best Day**: {best_day * 100:.2f}%",
            f"- **Worst Day**: {worst_day * 100:.2f}%",
            f"- **Win Rate**: {win_rate * 100:.1f}%",
            "",
            "### Monthly Returns",
        ]

        # Monthly returns table
        monthly = port_returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)
        for dt_idx, ret in monthly.tail(12).items():
            month_label = dt_idx.strftime("%Y-%m")
            lines.append(f"- {month_label}: {ret * 100:+.2f}%")

        return "\n".join(lines)

    # --- Helpers ---

    def _read(self) -> str:
        if self._file.exists():
            return self._file.read_text(encoding="utf-8")
        return _HEADER

    def _write(self, content: str) -> None:
        self._file.write_text(content, encoding="utf-8")

    def _remove_section(self, content: str, symbol: str) -> str:
        pattern = re.compile(r"^## " + re.escape(symbol) + r"\s*$", re.MULTILINE)
        m = pattern.search(content)
        if not m:
            return content
        start = m.start()
        next_h2 = re.search(r"^## ", content[m.end():], re.MULTILINE)
        end = m.end() + next_h2.start() if next_h2 else len(content)
        return content[:start] + content[end:]

    def _parse_positions(self) -> list[dict[str, Any]]:
        content = self._read()
        positions = []
        for m in re.finditer(r"^## ([A-Z0-9.]+)\s*$", content, re.MULTILINE):
            symbol = m.group(1)
            start = m.end()
            next_h2 = re.search(r"^## ", content[start:], re.MULTILINE)
            section = content[start:start + next_h2.start()] if next_h2 else content[start:]

            shares_m = re.search(r"\*\*Shares\*\*:\s*([\d.]+)", section)
            cost_m = re.search(r"\*\*Cost Basis\*\*:\s*\$([\d.]+)", section)
            date_m = re.search(r"\*\*Date\*\*:\s*(\d{4}-\d{2}-\d{2})", section)

            if shares_m and cost_m:
                positions.append({
                    "symbol": symbol,
                    "shares": float(shares_m.group(1)),
                    "cost_basis": float(cost_m.group(1)),
                    "date": date_m.group(1) if date_m else "",
                })
        return positions

    def _get_equal_weights(self, positions: list[dict]) -> dict[str, float]:
        n = len(positions)
        if n == 0:
            return {}
        w = 1.0 / n
        return {p["symbol"]: w for p in positions}
