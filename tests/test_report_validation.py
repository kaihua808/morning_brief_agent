from __future__ import annotations

import unittest

from main import render_email_html, validate_report
from rate_agent import MorningBriefReport


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
        "sources": [
            {
                "name": "Frankfurter API",
                "url": "https://example.test/rates",
                "data_date": "2026-08-14",
                "status": "ok",
            }
        ],
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
        warnings=["测试"],
        sources=make_brief()["sources"],
        email_subject="测试",
        email_body="测试",
    )


class ReportValidationTests(unittest.TestCase):
    def test_matching_report_passes(self) -> None:
        validate_report(make_report(), make_brief())

    def test_invented_report_date_is_rejected(self) -> None:
        report = make_report().model_copy(update={"report_date": "2025-07-04"})

        with self.assertRaisesRegex(ValueError, "report_date"):
            validate_report(report, make_brief())

    def test_invented_source_is_rejected(self) -> None:
        report = make_report()
        report.sources[0].name = "invented-source"

        with self.assertRaisesRegex(ValueError, "数据来源"):
            validate_report(report, make_brief())

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
