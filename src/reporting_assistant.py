from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = {
    "date", "facility", "shipments_dispatched", "on_time_rate",
    "defect_rate", "units_per_labor_hour", "staffed_hours"
}


def load_data(path: str) -> pd.DataFrame:
    """Load and validate the operational CSV."""
    df = pd.read_csv(path)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {sorted(missing)}")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        raise ValueError("Some dates could not be parsed.")
    numeric = [
        "shipments_dispatched", "on_time_rate", "defect_rate",
        "units_per_labor_hour", "staffed_hours"
    ]
    for col in numeric:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if df[numeric].isna().any().any():
        raise ValueError("Numeric KPI columns contain missing or invalid values.")
    if ((df["on_time_rate"] < 0) | (df["on_time_rate"] > 1)).any():
        raise ValueError("on_time_rate must be a decimal between 0 and 1.")
    if ((df["defect_rate"] < 0) | (df["defect_rate"] > 1)).any():
        raise ValueError("defect_rate must be a decimal between 0 and 1.")
    return df.sort_values("date").reset_index(drop=True)


def detect_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Flag unusual KPI observations using a robust median/MAD score."""
    result = df.copy()
    metrics = {
        "on_time_rate": "low",
        "defect_rate": "high",
        "units_per_labor_hour": "low",
        "shipments_dispatched": "either",
    }
    alerts = []
    for metric, direction in metrics.items():
        median = result[metric].median()
        mad = (result[metric] - median).abs().median()
        if mad == 0:
            delta = result[metric] - median
            score = delta.map(lambda value: 0.0 if value == 0 else (99.9 if value > 0 else -99.9))
        else:
            score = 0.6745 * (result[metric] - median) / mad
        if direction == "low":
            flagged = score < -3.5
        elif direction == "high":
            flagged = score > 3.5
        else:
            flagged = score.abs() > 3.5
        for idx in result.index[flagged]:
            alerts.append({
                "date": result.loc[idx, "date"].strftime("%Y-%m-%d"),
                "facility": str(result.loc[idx, "facility"]),
                "metric": metric,
                "observed_value": float(result.loc[idx, metric]),
                "baseline_median": float(median),
                "robust_score": round(float(score.loc[idx]), 2),
                "direction": direction,
            })
    return pd.DataFrame(alerts)


def build_analysis(df: pd.DataFrame, anomalies: pd.DataFrame) -> dict[str, Any]:
    """Create a compact, AI-ready analysis payload."""
    first_half = df.head(max(1, len(df) // 2))
    second_half = df.tail(max(1, len(df) - len(first_half)))
    return {
        "reporting_period": {
            "start": df["date"].min().strftime("%Y-%m-%d"),
            "end": df["date"].max().strftime("%Y-%m-%d"),
            "days": int(len(df)),
        },
        "overall_kpis": {
            "total_shipments": int(df["shipments_dispatched"].sum()),
            "average_daily_shipments": round(float(df["shipments_dispatched"].mean()), 1),
            "average_on_time_rate": round(float(df["on_time_rate"].mean()), 4),
            "average_defect_rate": round(float(df["defect_rate"].mean()), 4),
            "average_units_per_labor_hour": round(float(df["units_per_labor_hour"].mean()), 1),
            "total_staffed_hours": int(df["staffed_hours"].sum()),
        },
        "trend_comparison": {
            "on_time_rate_first_half": round(float(first_half["on_time_rate"].mean()), 4),
            "on_time_rate_second_half": round(float(second_half["on_time_rate"].mean()), 4),
            "defect_rate_first_half": round(float(first_half["defect_rate"].mean()), 4),
            "defect_rate_second_half": round(float(second_half["defect_rate"].mean()), 4),
            "productivity_first_half": round(float(first_half["units_per_labor_hour"].mean()), 1),
            "productivity_second_half": round(float(second_half["units_per_labor_hour"].mean()), 1),
        },
        "anomaly_count": int(len(anomalies)),
        "anomalies": anomalies.to_dict(orient="records") if not anomalies.empty else [],
    }


def deterministic_summary(analysis: dict[str, Any]) -> str:
    """Generate a report when no AI API key is configured."""
    k, t = analysis["overall_kpis"], analysis["trend_comparison"]
    lines = [
        "# Operations Performance Summary", "",
        f"**Period:** {analysis['reporting_period']['start']} to {analysis['reporting_period']['end']}", "",
        "## Executive summary",
        f"- Processed **{k['total_shipments']:,} shipments** across {analysis['reporting_period']['days']} reporting days.",
        f"- Average on-time rate was **{k['average_on_time_rate']:.1%}**.",
        f"- Average defect rate was **{k['average_defect_rate']:.1%}**.",
        f"- Average productivity was **{k['average_units_per_labor_hour']:.1f} units per labor hour**.",
        f"- The analysis flagged **{analysis['anomaly_count']} unusual KPI observations** for review.", "",
        "## Trend observations",
        f"- On-time rate: {t['on_time_rate_first_half']:.1%} in the first half vs. {t['on_time_rate_second_half']:.1%} in the second half.",
        f"- Defect rate: {t['defect_rate_first_half']:.1%} in the first half vs. {t['defect_rate_second_half']:.1%} in the second half.",
        f"- Productivity: {t['productivity_first_half']:.1f} vs. {t['productivity_second_half']:.1f} units per labor hour.", "",
        "## Recommended management follow-ups",
        "1. Review the dates and facilities associated with flagged KPI observations.",
        "2. Compare staffing, shipment mix, and operating conditions on unusual days before assigning root cause.",
        "3. Track the same KPIs in the next reporting period to determine whether changes persist.", "",
        "_Note: These are descriptive signals from simulated data, not proof of causation._",
    ]
    if analysis["anomalies"]:
        lines += ["", "## Anomaly alerts", ""]
        for a in analysis["anomalies"]:
            value = a["observed_value"]
            if a["metric"] in ("on_time_rate", "defect_rate"):
                value = f"{value:.1%}"
            lines.append(
                f"- **{a['date']} — {a['facility']} — {a['metric']}**: "
                f"{value} (baseline median: {a['baseline_median']:.3f}; "
                f"robust score: {a['robust_score']})."
            )
    return "\n".join(lines)


def claude_summary(analysis: dict[str, Any]) -> str:
    """Use Claude for an executive narrative; requires ANTHROPIC_API_KEY."""
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("Install the optional dependency with: pip install anthropic") from exc
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    model = os.getenv("CLAUDE_MODEL", "claude-3-5-haiku-latest")
    prompt = f"""
You are an operations analytics assistant writing for a fulfillment operations leader.
Use only the supplied data. Do not invent causes, targets, or facts. Distinguish observed
signals from hypotheses and note that anomalies need human validation. Provide a concise
executive summary, key KPI trends, anomaly alerts, and three prioritized follow-ups.

ANALYSIS DATA:
{json.dumps(analysis, indent=2)}
"""
    message = client.messages.create(
        model=model, max_tokens=1200, temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in message.content if getattr(block, "type", None) == "text")


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-Powered Operations Reporting Assistant")
    parser.add_argument("--input", default="data/sample_operations.csv", help="Path to operations CSV")
    parser.add_argument("--output", default="reports", help="Folder for generated reports")
    parser.add_argument("--use-claude", action="store_true", help="Use Claude API for narrative summary")
    args = parser.parse_args()
    df = load_data(args.input)
    anomalies = detect_anomalies(df)
    analysis = build_analysis(df, anomalies)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    if args.use_claude:
        if not os.getenv("ANTHROPIC_API_KEY"):
            raise SystemExit("Set ANTHROPIC_API_KEY before using --use-claude.")
        report = claude_summary(analysis)
    else:
        report = deterministic_summary(analysis)
    report_path = output_dir / "management_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"Analysis complete. Found {len(anomalies)} unusual KPI observations.")
    print(f"Management report: {report_path}")
    print(f"Structured analysis: {output_dir / 'analysis.json'}")


if __name__ == "__main__":
    main()
