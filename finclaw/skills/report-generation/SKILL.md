---
name: report-generation
description: Generate formatted financial reports — weekly summaries, morning briefs, and equity research
always: false
---

# Report Generation

This skill enables Finclaw to produce polished, comprehensive financial reports.

## Tools Available

- `report` — Generate weekly reports, morning briefs, equity research, and custom reports in markdown/HTML/PDF

## Report Types

### Weekly Report
Comprehensive portfolio and market review. Generate every Sunday:
1. Gather data from all tools
2. Call `report(action='weekly', format='markdown')` — it returns a template
3. Fill in each section by running the suggested tools
4. Combine into a cohesive narrative
5. For PDF output: `report(action='weekly', format='pdf')`

### Morning Brief
Enhanced daily brief with macro context:
1. Call `report(action='morning_brief')`
2. Execute the suggested tool calls for each section
3. Keep it concise — 1-2 paragraphs per section
4. Lead with the most important item

### Equity Research Report
Institutional-grade analysis for a single stock:
1. Call `report(action='equity_report', symbol='NVDA')`
2. Work through each section systematically:
   - Executive Summary (your thesis + rating + target)
   - Business Overview (from fundamentals)
   - Financial Analysis (income, balance sheet, cash flow)
   - Valuation (DCF, peer comps from fundamentals)
   - Technical Analysis (from technical_indicators)
   - Risk Assessment (your assessment)
   - Recommendation (synthesize everything)
3. Output as PDF for professional presentation

### Custom Report
User-specified sections:
```
report(action='custom', sections='[{"title": "Section 1", "content": "..."}]', format='html')
```

## Report Quality Guidelines

- **Lead with the verdict**: Start each section with the conclusion, then the evidence
- **Use concrete numbers**: "$242.50 (+2.3%)" not "up a bit"
- **Reference sources**: "Based on the 10-Q filed March 15..." or "FinBERT sentiment score: +0.32"
- **Compare to benchmarks**: "Outperformed SPY by 1.5%"
- **Flag changes**: "Changed from Neutral to Bullish because..."
- **Be actionable**: End with clear recommendations

## Weekly Report Cron
The weekly report should be generated via cron every Sunday at 5 PM ET:
```
cron(action='add', schedule='0 17 * * 0', tz='America/New_York',
     message='Generate a comprehensive weekly report covering portfolio, macro, watchlist, sentiment, and events.')
```
