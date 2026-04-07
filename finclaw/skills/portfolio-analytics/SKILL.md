---
name: portfolio-analytics
description: Portfolio management, optimization, backtesting, and performance analytics
always: false
---

# Portfolio Analytics

This skill enables Finclaw to manage and analyze an investment portfolio.

## Tools Available

- `portfolio` — Full portfolio management: positions, P&L, optimization, backtesting, tearsheets

## Portfolio Workflow

### Getting Started
When a user wants to track a portfolio:
1. Use `portfolio(action='add_position', symbol='AAPL', shares=100, cost_basis=150.00, date='2025-01-15')`
2. After adding all positions, run `portfolio(action='summary')` to show the current state
3. Suggest running `portfolio(action='analyze')` for risk/return metrics

### Regular Review
During weekly reviews:
1. `portfolio(action='summary')` — Current P&L and allocation
2. `portfolio(action='analyze', period='1y')` — Key metrics
3. Cross-reference with `macro_monitor(action='regime_check')` for risk context
4. Flag concentration risk if any position is >20% of portfolio
5. Suggest rebalancing if actual weights deviate >5% from targets

### Optimization
When asked to optimize:
1. Default to `efficient_frontier` for most users
2. Use `hrp` (Hierarchical Risk Parity) for diversification-focused portfolios
3. Use `black_litterman` when the user has strong market views
4. Always show both current and recommended weights
5. Explain the trade-offs: "Optimizing for max Sharpe suggests reducing AAPL from 25% to 18% and increasing XLF from 5% to 12%"

### Performance Reporting
- `portfolio(action='tearsheet')` generates comprehensive performance metrics
- Always include: Sharpe, Sortino, max drawdown, CAGR
- Compare to SPY as benchmark
- Use in weekly reports via `report(action='weekly')`

## Communication Style
- Lead with the bottom line: "Portfolio is up 3.2% this week, outperforming SPY by 1.1%"
- Flag risks proactively: "Concentration warning: 45% of portfolio is in Technology"
- Suggest actionable improvements: "Adding 10% TLT would reduce portfolio volatility by ~15%"
