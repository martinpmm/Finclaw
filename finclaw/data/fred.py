"""FRED API wrapper for macroeconomic data."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from finclaw.data.cache import TTLCache

_cache = TTLCache(default_ttl=3600)  # 1-hour default

# Key FRED series IDs
SERIES = {
    "fed_funds": "DFF",
    "cpi": "CPIAUCSL",
    "core_cpi": "CPILFESL",
    "unemployment": "UNRATE",
    "yield_2y": "DGS2",
    "yield_5y": "DGS5",
    "yield_10y": "DGS10",
    "yield_30y": "DGS30",
    "credit_spread_baa": "BAAFFM",
    "credit_spread_aaa": "AAAFFM",
    "vix": "VIXCLS",
    "initial_claims": "ICSA",
    "retail_sales": "RSXFS",
    "industrial_production": "INDPRO",
    "consumer_sentiment": "UMCSENT",
    "pce_inflation": "PCEPI",
}


def _get_fred(api_key: str):
    """Lazy-import and return a Fred client."""
    from fredapi import Fred
    return Fred(api_key=api_key)


def get_series(
    api_key: str,
    series_id: str,
    start: str | None = None,
    end: str | None = None,
    periods: int = 12,
) -> list[dict[str, Any]]:
    """Fetch a FRED series. Returns list of {date, value} dicts."""
    cache_key = f"fred:{series_id}:{start}:{end}:{periods}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    fred = _get_fred(api_key)
    if not start:
        start = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m-%d")
    if not end:
        end = datetime.now().strftime("%Y-%m-%d")

    data = fred.get_series(series_id, observation_start=start, observation_end=end)
    data = data.dropna().tail(periods)
    result = [
        {"date": idx.strftime("%Y-%m-%d"), "value": round(float(val), 4)}
        for idx, val in data.items()
    ]
    _cache.set(cache_key, result)
    return result


def get_yield_curve(api_key: str) -> dict[str, Any]:
    """Get current yield curve shape (2Y, 5Y, 10Y, 30Y)."""
    cache_key = "fred:yield_curve"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    fred = _get_fred(api_key)
    tenors = {"2Y": "DGS2", "5Y": "DGS5", "10Y": "DGS10", "30Y": "DGS30"}
    result: dict[str, Any] = {"tenors": {}}

    for label, series_id in tenors.items():
        data = fred.get_series(series_id).dropna()
        if not data.empty:
            result["tenors"][label] = round(float(data.iloc[-1]), 3)

    # Compute spreads
    t = result["tenors"]
    if "10Y" in t and "2Y" in t:
        result["spread_10y_2y"] = round(t["10Y"] - t["2Y"], 3)
        result["inverted"] = t["10Y"] < t["2Y"]
    if "30Y" in t and "10Y" in t:
        result["spread_30y_10y"] = round(t["30Y"] - t["10Y"], 3)

    _cache.set(cache_key, result)
    return result


def get_regime_indicators(api_key: str) -> dict[str, Any]:
    """Fetch key indicators for macro regime classification."""
    cache_key = "fred:regime_indicators"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    fred = _get_fred(api_key)
    indicators: dict[str, Any] = {}

    series_to_fetch = {
        "fed_funds_rate": "DFF",
        "cpi_yoy": "CPIAUCSL",
        "unemployment": "UNRATE",
        "vix": "VIXCLS",
        "credit_spread_baa": "BAAFFM",
        "yield_10y": "DGS10",
        "yield_2y": "DGS2",
        "initial_claims": "ICSA",
    }

    for name, series_id in series_to_fetch.items():
        try:
            data = fred.get_series(series_id).dropna()
            if not data.empty:
                current = float(data.iloc[-1])
                prev = float(data.iloc[-2]) if len(data) > 1 else current
                indicators[name] = {
                    "current": round(current, 4),
                    "previous": round(prev, 4),
                    "change": round(current - prev, 4),
                    "date": data.index[-1].strftime("%Y-%m-%d"),
                }
        except Exception:
            continue

    # Compute yield spread
    if "yield_10y" in indicators and "yield_2y" in indicators:
        spread = indicators["yield_10y"]["current"] - indicators["yield_2y"]["current"]
        indicators["yield_spread_10y_2y"] = {
            "current": round(spread, 4),
            "inverted": spread < 0,
        }

    _cache.set(cache_key, indicators)
    return indicators


def classify_regime(indicators: dict[str, Any]) -> dict[str, str]:
    """Classify the macro regime from indicators.

    Returns dict with 'risk' (risk_on/risk_off) and 'policy' (tightening/easing/neutral).
    """
    risk_off_signals = 0
    tightening_signals = 0
    total_signals = 0

    # VIX > 25 = risk off
    vix = indicators.get("vix", {})
    if vix:
        total_signals += 1
        if vix.get("current", 0) > 25:
            risk_off_signals += 1

    # Credit spread widening = risk off
    spread = indicators.get("credit_spread_baa", {})
    if spread:
        total_signals += 1
        if spread.get("current", 0) > 3.0:
            risk_off_signals += 1

    # Yield curve inversion = risk off
    ys = indicators.get("yield_spread_10y_2y", {})
    if ys:
        total_signals += 1
        if ys.get("inverted", False):
            risk_off_signals += 1

    # Rising unemployment = risk off
    unemp = indicators.get("unemployment", {})
    if unemp:
        total_signals += 1
        if unemp.get("change", 0) > 0.2:
            risk_off_signals += 1

    # Fed funds rising = tightening
    ff = indicators.get("fed_funds_rate", {})
    if ff:
        if ff.get("change", 0) > 0:
            tightening_signals += 1
        elif ff.get("change", 0) < 0:
            tightening_signals -= 1

    # Classify
    risk = "risk_off" if (total_signals > 0 and risk_off_signals / total_signals > 0.5) else "risk_on"
    if tightening_signals > 0:
        policy = "tightening"
    elif tightening_signals < 0:
        policy = "easing"
    else:
        policy = "neutral"

    return {"risk": risk, "policy": policy}
