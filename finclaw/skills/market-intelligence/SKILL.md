---
name: market-intelligence
description: Macro regime monitoring, financial sentiment analysis, and SEC filing intelligence
always: true
---

# Market Intelligence

This skill enables Finclaw to provide macro-aware, sentiment-enriched financial analysis.

## Tools Available

- `macro_monitor` — Track macroeconomic indicators (yield curve, CPI, unemployment, Fed funds, VIX) and classify the market regime
- `sentiment` — Score financial news and text using FinBERT for quantified bullish/bearish signals
- `sec_filings` — Search, read, and compare SEC EDGAR filings (10-K, 10-Q, 8-K, 13F)

## When to Use

### Macro Monitor
- **Always** run `macro_monitor(action='regime_check')` before giving portfolio-level advice
- Reference the current regime when analyzing any stock: "In the current risk-off / tightening environment..."
- Use `macro_monitor(action='yield_curve')` when discussing rate-sensitive sectors (financials, real estate, utilities)
- Use `macro_monitor(action='indicator', indicator='VIXCLS')` when VIX context is needed

### Sentiment
- Run `sentiment(action='analyze_stock', symbol='...')` whenever news is material to a thesis
- Use sentiment scores to quantify shifts: "Sentiment on NVDA has shifted from bullish (+0.35) to neutral (+0.02) over the past week"
- Run `sentiment(action='daily_summary')` during morning and evening briefings
- Use `sentiment(action='analyze_text')` when users share earnings call excerpts or research notes

### SEC Filings
- Use `sec_filings(action='search')` to check for recent filings when a stock has unusual price movement
- Run `sec_filings(action='financials')` for quarterly financial statement analysis
- Use `sec_filings(action='compare')` for QoQ trend analysis
- Cross-reference filing data with yfinance fundamentals for a complete picture
- After pulling a filing, use `documents(action='ingest_sec')` to store key insights

## Regime Classification

The macro monitor classifies the environment along two axes:

**Risk Appetite** (risk_on / risk_off):
- VIX > 25 = risk-off signal
- BAA credit spread > 3.0% = risk-off signal
- Yield curve inverted = risk-off signal
- Rising unemployment = risk-off signal

**Monetary Policy** (tightening / easing / neutral):
- Fed funds rate rising = tightening
- Fed funds rate falling = easing
- No change = neutral

## Morning Brief Workflow

When running a morning brief:
1. `macro_monitor(action='regime_check')` — Lead with the macro picture
2. `sentiment(action='daily_summary')` — Watchlist sentiment overview
3. `sec_filings(action='search')` for each watchlist stock — Flag new filings
4. `earnings_calendar(action='upcoming', days_ahead=3)` — Upcoming earnings
5. Synthesize into a concise morning message

## Integration with Analysis

When analyzing any watchlist stock:
1. Check the current macro regime from `macro_regime.json`
2. Run sentiment analysis on recent news
3. Check for recent SEC filings
4. Reference all three in your opinion: "Given the risk-on environment, bullish sentiment (+0.28), and strong Q3 10-Q results showing 15% revenue growth..."
