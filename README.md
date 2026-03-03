# Finclaw 🦅

**AI-powered financial assistant with proactive stock monitoring, watchlist tracking, and investment analysis.**

Finclaw is an open-source personal finance AI. It watches your stocks, forms its own opinions, tracks your investment thesis, and proactively alerts you to news and price movements — all through your preferred chat app (Telegram, Discord, Slack, CLI, and more).

---

## What Finclaw Does

- **Watchlist with memory** — Tell Finclaw which stocks you're interested in. It saves them, remembers your investment thesis, and keeps track of its own evolving opinions.
- **Daily price monitoring** — Checks prices at market open and close. Alerts you when something significant moves.
- **Proactive news scanning** — Monitors news for your watched stocks. Flags earnings, M&A, analyst upgrades, and regulatory news.
- **Opinionated analysis** — Finclaw forms a clear Bullish/Neutral/Bearish view on every stock, with conviction levels and reasoning. It updates its opinions when new information arrives.
- **Investment thesis tracking** — Share your thesis. Finclaw incorporates it into every analysis and tells you when news confirms or challenges it.
- **Discovery & suggestions** — Based on your interests and market conditions, Finclaw proactively suggests related stocks, ETFs, bonds, and strategies.
- **Deep analysis on demand** — Full fundamental + technical analysis, AI exposure scoring, or Wall Street-grade financial models.

---

## Quick Start

### 1. Install

```bash
cd finclaw
pip install -e .
```

### 2. Configure

```bash
finclaw onboard
```

This creates `~/.finclaw/config.json`. Add your LLM API key:

```json
{
  "providers": {
    "anthropic": { "apiKey": "sk-ant-..." }
  },
  "agents": {
    "defaults": {
      "model": "claude-opus-4-5",
      "provider": "anthropic"
    }
  }
}
```

### 3. Start chatting

```bash
# Interactive CLI
finclaw agent

# Single message
finclaw agent -m "Add AAPL to my watchlist. My thesis is that AI integration drives services growth."
```

### 4. Enable proactive alerts (optional)

For Telegram alerts, add to `~/.finclaw/config.json`:

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "your-bot-token",
      "allowFrom": ["your-telegram-user-id"]
    }
  }
}
```

Then start the gateway:

```bash
finclaw gateway
```

---

## Usage Examples

**Adding a stock with a thesis:**
```
You: Add NVDA to my watchlist. Thesis: AI infrastructure buildout drives continued growth.

Finclaw: Added NVDA. Current: $875.40 (+1.2%)
I'm Bullish | High conviction. Revenue grew 94% YoY. Your AI thesis is well-supported.
Main risk: valuation at 65x forward P/E and custom silicon competition from hyperscalers.
```

**Proactive daily update:**
```
Finclaw: 📊 Market Close — NVDA +1.9% | AAPL -0.8% | TSLA -3.1% ⚠️
TSLA delivery data looks mixed. Checking news... [analysis follows]
```

**Discovery suggestion:**
```
Finclaw: 💡 Given your AI infrastructure thesis, you might also watch SMCI
(Super Micro) — they make the servers running NVDA GPUs, up 200% YoY.
Want me to add it?
```

---

## Financial Tools

All data sourced from **yfinance** (free, no API key needed):

| Tool | Description |
|------|-------------|
| `stock_quote` | Real-time price, change, volume, market cap |
| `stock_history` | Historical OHLCV with performance summary |
| `fundamentals` | Valuation, margins, ROE, growth rates |
| `balance_sheet` | Assets, liabilities, equity |
| `cashflow` | Operating, investing, financing cash flows |
| `income_statement` | Revenue, expenses, profit |
| `insider_transactions` | Recent insider buying/selling |
| `technical_indicators` | RSI, MACD, Bollinger Bands, SMA/EMA, ATR |
| `stock_news` | Recent news for a stock |
| `market_news` | Broad market and macro news |
| `sector_performance` | All sector ETFs + benchmarks |
| `related_tickers` | Peers, competitors, related ETFs |
| `watchlist` | Manage watchlist with theses and opinions |

---

## Skills

| Skill | Description |
|-------|-------------|
| `stock-analysis` | Comprehensive fundamental + technical analysis with report |
| `ai-exposure` | 8-dimensional AI disruption exposure scoring |
| `fin-cog` | Wall Street-grade financial modeling (DCF, scenarios) |

---

## Proactive Monitoring

| Schedule | What happens |
|----------|-------------|
| Every 30 min | Price checks, major news alerts |
| Market open (9:30 AM ET) | Morning watchlist summary |
| Market close (4:00 PM ET) | End-of-day price summary |
| Weekly (Sunday) | Deep review + opinion updates + discovery suggestions |

---

## Roadmap

- [ ] Portfolio tracker (positions, P&L, allocation)
- [ ] Earnings calendar & pre/post earnings alerts
- [ ] Custom price alerts (target prices, technical triggers)
- [ ] Bull/Bear debate system
- [ ] Multi-asset (crypto, forex, commodities, bonds)
- [ ] Macro dashboard (Fed rates, CPI, VIX, yield curve)
- [ ] Social sentiment tracking
- [ ] Weekly PDF/HTML report generation
- [ ] Backtesting

---

## Built On

- **[nanobot](https://github.com/HKUDS/nanobot)** — The lightweight AI assistant framework Finclaw is based on
- **[yfinance](https://github.com/ranaroussi/yfinance)** — Financial data (free)
- **[stockstats](https://github.com/jealous/stockstats)** — Technical indicators
- **[LiteLLM](https://github.com/BerriAI/litellm)** — Multi-provider LLM support

## License

MIT
