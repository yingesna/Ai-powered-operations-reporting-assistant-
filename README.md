# AI-Powered Operations Reporting Assistant

A Python portfolio project that analyzes simulated fulfillment operations data, calculates KPIs, flags unusual observations, and generates a management report. An optional Claude API integration can turn the structured analysis into an executive-ready narrative.

> All included data is synthetic and created for demonstration. Do not use confidential employer, customer, employee, or shipment data.

## What it does
1. Loads and validates daily operations data from CSV.
2. Calculates shipment, on-time, defect, labor-productivity, and staffing metrics.
3. Detects unusual observations with a robust median-absolute-deviation score.
4. Compares the first and second halves of the reporting period.
5. Generates Markdown and JSON reports.
6. Optionally uses Claude to write the narrative and recommendations.

## Setup
Use Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run tests
```bash
python -m unittest discover -s tests -v
```

## Run the report
From the repository root:
```bash
python src/reporting_assistant.py
```
This creates `reports/management_report.md` and `reports/analysis.json`.

## Optional Claude integration
Install `anthropic`, set `ANTHROPIC_API_KEY` in your environment, and run:
```bash
python src/reporting_assistant.py --use-claude
```
Never commit API keys. The AI integration is optional and requires your own API access.

## Input CSV format
Required columns: `date`, `facility`, `shipments_dispatched`, `on_time_rate`, `defect_rate`, `units_per_labor_hour`, and `staffed_hours`. Rates must be decimals between 0 and 1.

## How anomaly detection works
For selected KPIs, the workflow calculates a robust score using the median and median absolute deviation (MAD). It flags unusually low on-time rate/productivity, unusually high defect rate, and unusually high or low shipment volume. This is a screening signal, not proof of a problem or its cause; flagged observations require human review.

## Limitations
- Sample data is synthetic.
- Trend comparison currently splits the reporting period into two halves.
- Production use would require seasonality-aware, facility-specific baselines and human review.
- The optional Claude integration sends the summarized KPI payload to Anthropic; review data-handling requirements before sending real business data.

