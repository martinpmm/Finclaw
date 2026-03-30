---
name: earnings-engine
description: Proactive earnings tracking with pre-briefs and post-earnings analysis
always: false
---

# Earnings Calendar & Event Engine

This skill makes Finclaw proactive about earnings — the most important regular catalyst for stock prices.

## Tools Available

- `earnings_calendar` — Track upcoming earnings, generate pre-briefs, analyze post-earnings results

## Proactive Behavior

### Daily Earnings Check
Every morning (or when the cron fires):
1. Run `earnings_calendar(action='upcoming', days_ahead=7)` for all watchlist stocks
2. For stocks reporting within 3 days, generate a pre-brief
3. Notify the user: "AAPL reports Thursday. Here's what to watch..."

### Pre-Earnings Brief
When a watchlist stock is about to report:
1. Run `earnings_calendar(action='pre_brief', symbol='...')`
2. Enrich with:
   - `sentiment(action='analyze_stock')` — current news sentiment
   - `options_flow(action='unusual')` — any unusual pre-earnings positioning
   - Watchlist thesis — what would confirm/invalidate it
3. Present as: "AAPL reports Thursday after close. Consensus: EPS $2.10, Revenue $94.3B. Your thesis is AI services growth — watch for Services revenue breakout above $26B."

### Post-Earnings Analysis
After a watchlist stock reports:
1. Run `earnings_calendar(action='post_analysis', symbol='...')`
2. Pull the 8-K filing: `sec_filings(action='get_filing', symbol='...', form_type='8-K')`
3. Run sentiment on earnings headlines: `sentiment(action='analyze_stock')`
4. Compare results to the pre-brief estimates
5. Update conviction: `watchlist(action='update_opinion', ...)`
6. Store in memory: `memory_query(action='store', ticker='...', analysis_type='earnings_review', ...)`
7. Notify user with summary

## What to Watch in Each Earnings Report
- **Revenue**: Beat/miss vs consensus, growth rate YoY and QoQ
- **EPS**: Beat/miss, quality of earnings (one-time items?)
- **Margins**: Gross, operating, net — expanding or compressing?
- **Guidance**: Forward estimates raised, maintained, or lowered?
- **Segment Data**: Any standout segments relevant to the thesis?
- **Management Commentary**: Tone on key thesis drivers

## Communication Format
Pre-earnings:
> **AAPL reports Thursday 4:30 PM ET**
> Consensus: EPS $2.10 | Revenue $94.3B
> Your thesis: AI services growth. Watch for Services >$26B.
> Options: Unusual call buying at $200 strike (3.5x volume/OI)
> Sentiment: Neutral-to-bullish (+0.12)

Post-earnings:
> **AAPL Q1 Results**
> EPS: $2.18 (beat by $0.08) | Revenue: $95.1B (beat by $0.8B)
> Services: $27.2B (record — confirms your thesis)
> Guidance: Raised Q2 revenue range to $88-92B
> Recommendation: Maintain Bullish, raise conviction to High
