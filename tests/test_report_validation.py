from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from email_template import render_email_html
from main import build_report, save_report, validate_report
from rate_agent import MorningBriefNarrative, MorningBriefReport


def make_brief() -> dict:
    return {
        "report_date": "2026-08-14",
        "effective_date": "2026-08-14",
        "usd_cny_rate": 6.74,
        "usd_amount": 20.0,
        "cny_cost": 134.8,
        "observation_count": 14,
        "position_percentile": 20.0,
        "position_label": "近期低位",
        "trend_change_percent": -0.1,
        "trend_label": "短期震荡",
        "base_recommendation": "现在充比较划算",
    }


def make_report() -> MorningBriefReport:
    return MorningBriefReport(
        report_date="2026-08-14",
        effective_rate_date="2026-08-14",
        usd_cny_rate=6.74,
        usd_amount=20.0,
        cny_cost=134.8,
        observation_count=14,
        position_percentile=20.0,
        position_label="近期低位",
        trend_change_percent=-0.1,
        trend_label="短期震荡",
        recommendation="现在充比较划算",
        rationale=["测试"],
        email_subject="测试",
        email_body="测试",
    )


class ReportValidationTests(unittest.TestCase):
    def test_build_report_uses_tool_data_and_model_rationale(self) -> None:
        narrative = MorningBriefNarrative(
            rationale=["汇率处于近期低位。", "短期走势相对平稳。"],
        )

        report = build_report(narrative, make_brief())

        self.assertEqual(report.report_date, "2026-08-14")
        self.assertEqual(report.effective_rate_date, "2026-08-14")
        self.assertEqual(report.usd_cny_rate, 6.74)
        self.assertEqual(report.cny_cost, 134.8)
        self.assertEqual(report.recommendation, "现在充比较划算")
        self.assertEqual(report.rationale, narrative.rationale)
        self.assertEqual(
            report.email_subject,
            "【每日晨报】2026-08-14 汇率建议：现在充比较划算",
        )

    def test_matching_report_passes(self) -> None:
        validate_report(make_report(), make_brief())

    def test_invented_report_date_is_rejected(self) -> None:
        report = make_report().model_copy(update={"report_date": "2025-07-04"})

        with self.assertRaisesRegex(ValueError, "report_date"):
            validate_report(report, make_brief())

    def test_report_excludes_warnings_and_sources(self) -> None:
        report_data = make_report().model_dump()

        self.assertNotIn("warnings", report_data)
        self.assertNotIn("sources", report_data)

    def test_saved_report_contains_run_id(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "latest_report.json"
            with patch("main.OUTPUT_PATH", output_path):
                save_report(make_report(), "20260815T093000+0800")

            report_data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(report_data["run_id"], "20260815T093000+0800")

    def test_email_body_is_html_and_excludes_unwanted_sections(self) -> None:
        email_body = render_email_html(make_report())

        self.assertIn('<html lang="zh-CN">', email_body)
        self.assertIn("今日充值建议", email_body)
        self.assertIn("判断理由", email_body)
        self.assertNotIn("## 汇率简报", email_body)
        self.assertNotIn("风险提醒", email_body)
        self.assertNotIn("数据来源", email_body)
        self.assertNotIn("不构成投资建议", email_body)


if __name__ == "__main__":
    unittest.main()
