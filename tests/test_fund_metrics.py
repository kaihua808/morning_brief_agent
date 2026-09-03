from __future__ import annotations

import unittest
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from fund_metrics import (
    build_fund_brief,
    calculate_max_drawdown,
    calculate_period_change,
    calculate_range_position,
    load_fund_sample,
)


class FundMetricCalculationTests(unittest.TestCase):
    def test_period_change_rising(self) -> None:
        result = calculate_period_change(
            [1.00, 1.01, 1.02, 1.03, 1.04, 1.05],
            5,
        )
        self.assertAlmostEqual(result, 5.00, places=2)

    def test_period_change_falling(self) -> None:
        result = calculate_period_change(
            [1.00, 0.99, 0.98, 0.97, 0.96, 0.95],
            5,
        )
        self.assertAlmostEqual(result, -5.00, places=2)

    def test_range_position_uses_last_value(self) -> None:
        highest, lowest, position = calculate_range_position([1.00, 1.20, 1.10])

        self.assertEqual(highest, 1.20)
        self.assertEqual(lowest, 1.00)
        self.assertAlmostEqual(position, 50.00, places=2)

    def test_range_position_rejects_flat_range(self) -> None:
        with self.assertRaises(ValueError):
            calculate_range_position([1.00, 1.00, 1.00])

    def test_max_drawdown(self) -> None:
        result = calculate_max_drawdown([1.00, 1.20, 1.10, 0.90, 1.15])
        self.assertAlmostEqual(result, -25.00, places=2)

    def test_max_drawdown_ignores_low_before_peak(self) -> None:
        result = calculate_max_drawdown([0.90, 1.20])
        self.assertEqual(result, 0.0)

    def test_max_drawdown_is_zero_when_values_only_rise(self) -> None:
        result = calculate_max_drawdown([1.00, 1.10, 1.20])
        self.assertEqual(result, 0.0)


class FundBriefStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fund_df = load_fund_sample()
        cls.latest_date = pd.to_datetime(fund_df["净值日期"]).max().date()

    def test_unsupported_fund_is_blocked(self) -> None:
        result = build_fund_brief("000001")

        self.assertEqual(result["calculation_status"], "blocked")
        self.assertIsNone(result["metrics"])
        self.assertTrue(result["error"])

    def test_fresh_data_returns_all_metrics(self) -> None:
        result = build_fund_brief(
            "006131",
            reference_date=self.latest_date + timedelta(days=1),
            refresh_data=False,
        )

        self.assertEqual(result["data_status"], "normal")
        self.assertEqual(result["calculation_status"], "completed")
        self.assertIsNone(result["error"])

        expected_fields = {
            "latest_nav",
            "change_5d_percent",
            "change_20d_percent",
            "highest_20d",
            "lowest_20d",
            "position_20d_percent",
            "max_drawdown_20d_percent",
        }
        self.assertEqual(set(result["metrics"]), expected_fields)
        for field in expected_fields:
            self.assertIsNotNone(result["metrics"][field])

    def test_delayed_data_is_blocked(self) -> None:
        result = build_fund_brief(
            "006131",
            reference_date=self.latest_date + timedelta(days=30),
            refresh_data=False,
        )

        self.assertEqual(result["data_status"], "delayed")
        self.assertEqual(result["calculation_status"], "blocked")
        self.assertIsNone(result["metrics"])

    def test_four_day_boundary_is_normal(self) -> None:
        result = build_fund_brief(
            "006131",
            reference_date=self.latest_date + timedelta(days=4),
            refresh_data=False,
        )
        self.assertEqual(result["data_status"], "normal")

    def test_five_day_boundary_is_delayed(self) -> None:
        result = build_fund_brief(
            "006131",
            reference_date=self.latest_date + timedelta(days=5),
            refresh_data=False,
        )
        self.assertEqual(result["data_status"], "delayed")

    def test_reference_date_before_data_is_invalid(self) -> None:
        result = build_fund_brief(
            "006131",
            reference_date=self.latest_date - timedelta(days=1),
            refresh_data=False,
        )

        self.assertEqual(result["data_status"], "invalid")
        self.assertEqual(result["calculation_status"], "blocked")


class FundBriefInvalidDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_path = Path(self.temp_dir.name) / "fund.csv"
        self.valid_df = pd.DataFrame(
            {
                "净值日期": pd.date_range("2026-08-01", periods=21, freq="D"),
                "单位净值": [1.00 + index / 100 for index in range(21)],
            }
        )
        self.reference_date = self.valid_df["净值日期"].iloc[-1].date() + timedelta(
            days=1
        )

    def write_data(self, fund_df: pd.DataFrame) -> None:
        fund_df.to_csv(self.data_path, index=False)

    def assert_blocked_with_status(self, result, expected_status: str) -> None:
        self.assertEqual(result["data_status"], expected_status)
        self.assertEqual(result["calculation_status"], "blocked")
        self.assertIsNone(result["metrics"])
        self.assertTrue(result["error"])

    def test_missing_file(self) -> None:
        result = build_fund_brief(
            "006131",
            reference_date=self.reference_date,
            data_path=self.data_path,
        )
        self.assert_blocked_with_status(result, "missing")

    def test_missing_required_column(self) -> None:
        self.write_data(self.valid_df.drop(columns=["单位净值"]))
        result = build_fund_brief(
            "006131",
            reference_date=self.reference_date,
            data_path=self.data_path,
        )
        self.assert_blocked_with_status(result, "missing")

    def test_invalid_date_text(self) -> None:
        fund_df = self.valid_df.copy()
        fund_df["净值日期"] = fund_df["净值日期"].astype("object")
        fund_df.loc[0, "净值日期"] = "不是日期"
        self.write_data(fund_df)
        result = build_fund_brief(
            "006131",
            reference_date=self.reference_date,
            data_path=self.data_path,
        )
        self.assert_blocked_with_status(result, "invalid")

    def test_insufficient_rows(self) -> None:
        self.write_data(self.valid_df.head(20))
        result = build_fund_brief(
            "006131",
            reference_date=self.reference_date,
            data_path=self.data_path,
        )
        self.assert_blocked_with_status(result, "insufficient")

    def test_missing_nav(self) -> None:
        fund_df = self.valid_df.copy()
        fund_df.loc[0, "单位净值"] = None
        self.write_data(fund_df)
        result = build_fund_brief(
            "006131",
            reference_date=self.reference_date,
            data_path=self.data_path,
        )
        self.assert_blocked_with_status(result, "missing")

    def test_non_positive_nav(self) -> None:
        fund_df = self.valid_df.copy()
        fund_df.loc[0, "单位净值"] = 0
        self.write_data(fund_df)
        result = build_fund_brief(
            "006131",
            reference_date=self.reference_date,
            data_path=self.data_path,
        )
        self.assert_blocked_with_status(result, "invalid")


if __name__ == "__main__":
    unittest.main()
