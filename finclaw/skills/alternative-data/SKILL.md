---
name: alternative-data
description: Social sentiment, institutional holdings, options flow, and enhanced insider analysis
always: false
---

# Alternative Data & Signals

This skill combines non-traditional data sources to build conviction signals beyond price and fundamentals.

## Tools Available

- `social_sentiment` — Reddit financial community sentiment (r/wallstreetbets, r/stocks, r/investing)
- `institutional_holdings` — 13F institutional holder data
- `options_flow` — Options chain analysis and unusual activity detection
- `insider_transactions` — (existing) Insider buying/selling activity

## Signal Combination Framework

When building a conviction signal for a stock, combine all four sources:

### 1. Social Sentiment
- Run `social_sentiment(action='reddit', symbol='...')`
- High mention count + positive sentiment = retail bullishness
- Sudden spike in mentions can precede price moves
- Weight: supplementary (don't base decisions solely on Reddit)

### 2. Institutional Holdings
- Run `institutional_holdings(action='holders', symbol='...')`
- Look for: increasing institutional ownership, new positions from top funds
- Flag: "Bridgewater added 400K shares of XYZ last quarter"
- Cross-reference with the user's thesis

### 3. Options Flow
- Run `options_flow(action='unusual', symbol='...')` for unusual activity
- Run `options_flow(action='summary', symbol='...')` for put/call sentiment
- High call volume + low put/call ratio = bullish positioning
- Unusual activity before earnings can signal institutional conviction
- Weight: moderate (smart money signal)

### 4. Insider Transactions
- Run `insider_transactions(symbol='...')`
- Cross-reference with the user's thesis:
  - "The CFO just sold $2M in shares, but your thesis was margin recovery. Worth revisiting."
  - "Three insiders bought in the last month — aligns with your bullish thesis"
- Weight: high (insiders know the business best)

## Conviction Scoring

Combine signals into an overall conviction assessment:
- **4/4 aligned** (all bullish or all bearish): "Strong conviction"
- **3/4 aligned**: "Moderate conviction, with [dissenting signal] as a counterpoint"
- **2/4 aligned**: "Mixed signals — worth investigating further"
- **<2 aligned**: "No clear signal from alternative data"

## When to Run
- During deep-dive stock analyses
- Before/after earnings (options flow is especially useful pre-earnings)
- When a watchlist stock has unusual price movement
- During weekly reviews for the most-watched stocks
