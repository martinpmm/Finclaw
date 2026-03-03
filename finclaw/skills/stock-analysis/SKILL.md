---
name: stock-analysis
description: Comprehensive stock analysis with fundamental analysis (financial metrics, business quality, valuation), technical analysis (indicators, chart patterns), stock comparisons, and investment report generation. Use when user requests deep analysis of stock tickers (e.g., "analyze AAPL", "compare TSLA vs NVDA", "give me a full report on Microsoft").
---

# Stock Analysis

## Overview

Perform comprehensive analysis of stocks covering fundamental analysis (financials, business quality, valuation), technical analysis (indicators, trends, patterns), peer comparisons, and generate detailed investment reports. Uses Finclaw's built-in financial data tools for real-time data.

## Data Tools Available

Use these built-in tools — no web search needed for financial data:

| Tool | What it returns |
|------|----------------|
| `stock_quote(symbol)` | Current price, day change, volume, market cap, P/E, 52-week range |
| `stock_history(symbol, period)` | Historical OHLCV data with performance summary |
| `fundamentals(symbol)` | Valuation, profitability, growth, financial health metrics |
| `balance_sheet(symbol, freq)` | Assets, liabilities, equity |
| `cashflow(symbol, freq)` | Operating/investing/financing cash flows |
| `income_statement(symbol, freq)` | Revenue, expenses, profit |
| `insider_transactions(symbol)` | Recent insider buying/selling |
| `technical_indicators(symbol, indicators)` | RSI, MACD, Bollinger Bands, SMA/EMA, ATR |
| `stock_news(symbol)` | Recent news articles |
| `related_tickers(symbol)` | Peers, competitors, sector ETFs |
| `sector_performance(period)` | All sectors and benchmarks comparison |

Also check `WATCHLIST.md` — if the stock is watched, reference the user's thesis and your existing opinion.

## Analysis Types

1. **Basic Stock Info** - Quick overview with key metrics
2. **Fundamental Analysis** - Deep dive into business, financials, valuation
3. **Technical Analysis** - Chart patterns, indicators, trend analysis
4. **Comprehensive Report** - Complete analysis combining all approaches

## Analysis Workflows

### 1. Basic Stock Information

**Steps:**
1. `stock_quote(symbol)` — price, change, volume, market cap, P/E
2. `stock_news(symbol, limit=5)` — recent developments
3. Present concise summary with investment context

### 2. Fundamental Analysis

**Steps:**
1. `fundamentals(symbol)` — all key ratios and metrics
2. `income_statement(symbol, freq="quarterly")` — recent 4 quarters
3. `cashflow(symbol, freq="quarterly")` — free cash flow trend
4. Read `references/fundamental-analysis.md` for analytical framework
5. Read `references/financial-metrics.md` for metric definitions
6. Generate output following `references/report-template.md`

**Critical analyses:**
- Profitability trends (improving/declining margins)
- Cash flow quality (FCF vs reported earnings)
- Balance sheet strength (debt, liquidity)
- Growth sustainability (revenue + EPS trends)
- Valuation vs peers and historical average

### 3. Technical Analysis

**Steps:**
1. `technical_indicators(symbol, indicators=["rsi", "macd", "macds", "macdh", "boll", "boll_ub", "boll_lb", "close_50_sma", "close_200_sma"])` — key indicators
2. `stock_history(symbol, period="3mo")` — recent price action
3. Read `references/technical-analysis.md` for interpretation framework
4. Identify trend, support/resistance, overbought/oversold, and pattern signals

### 4. Comprehensive Investment Report

**Steps:**
1. Gather all data: `stock_quote`, `fundamentals`, `income_statement`, `cashflow`, `technical_indicators`, `stock_news`, `related_tickers`
2. Read `references/report-template.md` for structure
3. Synthesize: bull case + bear case + recommendation
4. Generate report: Buy/Hold/Sell + target price + conviction + entry strategy

## Stock Comparison Analysis

**Steps:**
1. Run `stock_quote` + `fundamentals` + `technical_indicators` for each ticker
2. Create side-by-side metrics table
3. Identify relative strengths (fundamentals, technicals, valuation)
4. Generate recommendation: which is more attractive and why

## Reference Files

Load these from the skill directory when needed:

- `references/fundamental-analysis.md` — Business quality, financial health, valuation frameworks, red flags
- `references/technical-analysis.md` — Indicator definitions, chart patterns, support/resistance
- `references/financial-metrics.md` — All key metric formulas and definitions
- `references/report-template.md` — Complete report structure and formatting

## Output Guidelines

- Use tables for financial data and comparisons
- Bold key metrics and findings
- Present both bull and bear perspectives
- Always integrate context from WATCHLIST.md if stock is watched
- Reference the user's investment thesis when giving recommendations
- Include conviction level and key risk factors
