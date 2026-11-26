import unittest
from pathlib import Path
import pandas as pd

from src.reporting_assistant import REQUIRED_COLUMNS, build_analysis, detect_anomalies, load_data

ROOT = Path(__file__).resolve().parents[1]


class ReportingAssistantTests(unittest.TestCase):
    def test_sample_data_loads_and_has_required_columns(self):
        df = load_data(str(ROOT / "data" / "sample_operations.csv"))
        self.assertTrue(REQUIRED_COLUMNS.issubset(df.columns))
        self.assertEqual(len(df), 30)
        self.assertTrue(df["date"].is_monotonic_increasing)

    def test_anomaly_detector_flags_injected_low_on_time_observation(self):
        df = pd.DataFrame({
            "date": pd.date_range("2026-01-01", periods=12),
            "facility": ["FC-A"] * 12,
            "shipments_dispatched": [1000] * 12,
            "on_time_rate": [0.97] * 11 + [0.70],
            "defect_rate": [0.02] * 12,
            "units_per_labor_hour": [110.0] * 12,
            "staffed_hours": [90] * 12,
        })
        alerts = detect_anomalies(df)
        self.assertIn("on_time_rate", alerts["metric"].tolist())

    def test_analysis_contains_management_kpis(self):
        df = load_data(str(ROOT / "data" / "sample_operations.csv"))
        anomalies = detect_anomalies(df)
        analysis = build_analysis(df, anomalies)
        self.assertGreater(analysis["overall_kpis"]["total_shipments"], 0)
        self.assertIn("trend_comparison", analysis)
        self.assertEqual(analysis["anomaly_count"], len(anomalies))

    def test_invalid_rate_is_rejected(self):
        bad = ROOT / "tests" / "invalid_rate_fixture.csv"
        bad.write_text(
            "date,facility,shipments_dispatched,on_time_rate,defect_rate,units_per_labor_hour,staffed_hours\n"
            "2026-01-01,FC-A,100,1.2,0.02,100,8\n",
            encoding="utf-8",
        )
        try:
            with self.assertRaises(ValueError):
                load_data(str(bad))
        finally:
            bad.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
