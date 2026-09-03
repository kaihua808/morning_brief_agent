from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from fund_data_probe import refresh_fund_sample
from fund_metrics import SAMPLE_DATA_PATH, build_fund_brief


def make_candidate() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "净值日期": pd.date_range("2026-08-01", periods=21, freq="D"),
            "单位净值": [1.00 + index / 100 for index in range(21)],
            "日增长率": [0.0] + [1.0] * 20,
        }
    )


class FundRefreshTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.destination = Path(self.temp_dir.name) / "fund.csv"
        self.destination.write_text("原有可信数据", encoding="utf-8")

    @patch("fund_data_probe.ak.fund_open_fund_info_em")
    def test_valid_candidate_replaces_local_csv(self, mock_fetch) -> None:
        mock_fetch.return_value = make_candidate()

        refreshed = refresh_fund_sample("006131", self.destination)

        saved = pd.read_csv(self.destination)
        self.assertEqual(len(refreshed), 21)
        self.assertEqual(len(saved), 21)
        self.assertEqual(saved["净值日期"].iloc[-1], "2026-08-21")

    @patch("fund_data_probe.ak.fund_open_fund_info_em")
    def test_fetch_failure_keeps_existing_csv(self, mock_fetch) -> None:
        original = self.destination.read_bytes()
        mock_fetch.side_effect = RuntimeError("模拟网络失败")

        with self.assertRaisesRegex(RuntimeError, "模拟网络失败"):
            refresh_fund_sample("006131", self.destination)

        self.assertEqual(original, self.destination.read_bytes())

    @patch("fund_data_probe.ak.fund_open_fund_info_em")
    def test_invalid_candidate_keeps_existing_csv(self, mock_fetch) -> None:
        original = self.destination.read_bytes()
        mock_fetch.return_value = make_candidate().drop(columns=["单位净值"])

        with self.assertRaisesRegex(ValueError, "缺少必要字段"):
            refresh_fund_sample("006131", self.destination)

        self.assertEqual(original, self.destination.read_bytes())

    @patch("fund_metrics.refresh_fund_sample")
    def test_refresh_failure_blocks_metric_calculation(self, mock_refresh) -> None:
        mock_refresh.side_effect = RuntimeError("模拟刷新失败")

        result = build_fund_brief("006131", data_path=SAMPLE_DATA_PATH)

        self.assertEqual(result["data_status"], "refresh_failed")
        self.assertEqual(result["calculation_status"], "blocked")
        self.assertIsNone(result["metrics"])
        self.assertIn("模拟刷新失败", result["error"])


if __name__ == "__main__":
    unittest.main()
