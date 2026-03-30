"""Macro monitor tool: macroeconomic data and regime classification via FRED."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from finclaw.agent.tools.base import Tool


class MacroMonitorTool(Tool):
    """Track macroeconomic indicators and classify the current market regime."""

    def __init__(self, workspace: Path, fred_api_key: str | None = None) -> None:
        self._workspace = workspace
        self._fred_api_key = fred_api_key
        self._regime_file = workspace / "macro_regime.json"

    @property
    def name(self) -> str:
        return "macro_monitor"

    @property
    def description(self) -> str:
        return (
            "Track macroeconomic indicators and classify the current market regime. "
            "Uses FRED data to monitor yield curves, CPI, unemployment, Fed funds rate, "
            "credit spreads, and VIX. Generates a regime classification (risk-on/risk-off, "
            "tightening/easing) that provides context for all investment analysis. "
            "Actions: regime_check, yield_curve, indicator, history."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["regime_check", "yield_curve", "indicator", "history"],
                    "description": (
                        "regime_check: classify current macro environment; "
                        "yield_curve: get current yield curve shape and spreads; "
                        "indicator: get a specific FRED series; "
                        "history: show cached regime history"
                    ),
                },
                "indicator": {
                    "type": "string",
                    "description": (
                        "FRED series ID for 'indicator' action. Common: DFF (Fed funds), "
                        "CPIAUCSL (CPI), UNRATE (unemployment), VIXCLS (VIX), "
                        "DGS10 (10Y yield), BAAFFM (BAA credit spread), ICSA (initial claims)"
                    ),
                },
                "period": {
                    "type": "string",
                    "enum": ["3mo", "6mo", "1y", "2y", "5y"],
                    "description": "Lookback period for indicator history. Default: 1y.",
                },
            },
            "required": ["action"],
        }

    async def execute(self, action: str, **kwargs: Any) -> str:
        if not self._fred_api_key:
            return (
                "Error: FRED API key not configured. "
                "Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html "
                "and add it to your Finclaw config under tools.financial_data.fred_api_key."
            )

        try:
            from finclaw.data import fred
        except ImportError:
            return (
                "Error: fredapi is not installed. "
                "Install with: pip install finclaw[market-intel]"
            )

        if action == "regime_check":
            return self._regime_check(fred)
        if action == "yield_curve":
            return self._yield_curve(fred)
        if action == "indicator":
            return self._indicator(fred, kwargs.get("indicator", ""), kwargs.get("period", "1y"))
        if action == "history":
            return self._history()
        return f"Unknown action: {action}"

    def _regime_check(self, fred_mod) -> str:
        try:
            indicators = fred_mod.get_regime_indicators(self._fred_api_key)
            regime = fred_mod.classify_regime(indicators)

            # Save to history
            self._save_regime(regime, indicators)

            lines = [
                "## Macro Regime Check",
                "",
                f"**Regime**: {regime['risk'].replace('_', ' ').title()} / {regime['policy'].title()}",
                "",
                "### Key Indicators",
            ]

            for name, data in indicators.items():
                if isinstance(data, dict) and "current" in data:
                    change_str = ""
                    if "change" in data:
                        change = data["change"]
                        arrow = "+" if change > 0 else ""
                        change_str = f" ({arrow}{change})"
                    lines.append(
                        f"- **{name.replace('_', ' ').title()}**: "
                        f"{data['current']}{change_str} (as of {data.get('date', 'N/A')})"
                    )
                elif isinstance(data, dict) and "inverted" in data:
                    status = "INVERTED" if data["inverted"] else "normal"
                    lines.append(
                        f"- **{name.replace('_', ' ').title()}**: "
                        f"{data['current']} ({status})"
                    )

            lines += [
                "",
                "### Regime Classification",
                f"- **Risk appetite**: {regime['risk'].replace('_', ' ').title()}",
                f"- **Monetary policy**: {regime['policy'].title()}",
            ]

            return "\n".join(lines)
        except Exception as e:
            return f"Error running regime check: {e}"

    def _yield_curve(self, fred_mod) -> str:
        try:
            yc = fred_mod.get_yield_curve(self._fred_api_key)
            tenors = yc.get("tenors", {})

            lines = [
                "## Yield Curve",
                "",
                "| Tenor | Yield |",
                "|---|---|",
            ]
            for tenor, value in tenors.items():
                lines.append(f"| {tenor} | {value}% |")

            lines.append("")
            if "spread_10y_2y" in yc:
                status = "**INVERTED**" if yc.get("inverted") else "Normal"
                lines.append(f"**10Y-2Y Spread**: {yc['spread_10y_2y']}% ({status})")
            if "spread_30y_10y" in yc:
                lines.append(f"**30Y-10Y Spread**: {yc['spread_30y_10y']}%")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching yield curve: {e}"

    def _indicator(self, fred_mod, indicator: str, period: str) -> str:
        if not indicator:
            # Show available indicators
            lines = ["## Available FRED Indicators", ""]
            for label, series_id in fred_mod.SERIES.items():
                lines.append(f"- **{label}**: `{series_id}`")
            return "\n".join(lines)

        period_map = {"3mo": 6, "6mo": 12, "1y": 24, "2y": 48, "5y": 120}
        periods = period_map.get(period, 24)

        try:
            data = fred_mod.get_series(self._fred_api_key, indicator.upper(), periods=periods)
            if not data:
                return f"No data found for FRED series: {indicator}"

            lines = [
                f"## FRED Series: {indicator.upper()} (last {period})",
                "",
                "| Date | Value |",
                "|---|---|",
            ]
            for point in data:
                lines.append(f"| {point['date']} | {point['value']} |")

            if len(data) >= 2:
                first = data[0]["value"]
                last = data[-1]["value"]
                change = last - first
                pct = (change / first * 100) if first != 0 else 0
                lines.append(f"\n**Change over period**: {change:+.4f} ({pct:+.2f}%)")

            return "\n".join(lines)
        except Exception as e:
            return f"Error fetching indicator {indicator}: {e}"

    def _history(self) -> str:
        if not self._regime_file.exists():
            return "No regime history available. Run regime_check first."

        try:
            data = json.loads(self._regime_file.read_text(encoding="utf-8"))
            history = data.get("history", [])

            if not history:
                return "No regime history recorded yet."

            lines = ["## Macro Regime History", "", "| Date | Risk | Policy |", "|---|---|---|"]
            for entry in history[-20:]:  # Last 20 entries
                lines.append(
                    f"| {entry['date']} | {entry['risk'].replace('_', ' ').title()} | "
                    f"{entry['policy'].title()} |"
                )

            return "\n".join(lines)
        except Exception as e:
            return f"Error reading regime history: {e}"

    def _save_regime(self, regime: dict, indicators: dict) -> None:
        """Append regime check to history file."""
        try:
            if self._regime_file.exists():
                data = json.loads(self._regime_file.read_text(encoding="utf-8"))
            else:
                data = {"history": []}

            data["current"] = {
                "risk": regime["risk"],
                "policy": regime["policy"],
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "indicators": {
                    k: v.get("current") if isinstance(v, dict) and "current" in v else v
                    for k, v in indicators.items()
                },
            }
            data["history"].append({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "risk": regime["risk"],
                "policy": regime["policy"],
            })
            # Keep last 365 entries
            data["history"] = data["history"][-365:]

            self._regime_file.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
        except Exception:
            pass
