from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from fund_agent import FundBriefReport
from fund_html import render_fund_html
from fund_main import save_fund_html


def make_report() -> FundBriefReport:
    return FundBriefReport(
        fund_code="006131",
        data_date="2026-08-31",
        age_calendar_days=3,
        freshness_basis="calendar_days",
        data_status="normal",
        calculation_status="completed",
        latest_nav=1.1477,
        change_5d_percent=1.35,
        change_20d_percent=1.82,
        highest_20d=1.1740,
        lowest_20d=1.1301,
        position_20d_percent=40.09,
        max_drawdown_20d_percent=-3.74,
        summary="近5日与近20日方向一致。",
        risk_note="当前更靠近区间低点，期间曾出现回落。",
        behavior_reminder="不要只根据短期上涨决定申购。",
    )


class FundHtmlTests(unittest.TestCase):
    def test_report_fields_are_rendered(self) -> None:
        html = render_fund_html(make_report())

        expected_texts = (
            "基金 006131 晨报",
            "2026-08-31",
            "1.1477",
            "+1.35%",
            "+1.82%",
            "40.09%",
            "-3.74%",
            "近5日与近20日方向一致。",
            "当前更靠近区间低点，期间曾出现回落。",
            "不要只根据短期上涨决定申购。",
        )
        for text in expected_texts:
            self.assertIn(text, html)

    def test_model_text_is_html_escaped(self) -> None:
        report = make_report().model_copy(
            update={"summary": "<script>alert('x')</script>"}
        )

        html = render_fund_html(report)

        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;", html)
        self.assertNotIn("<script>alert('x')</script>", html)

    def test_render_does_not_change_report(self) -> None:
        report = make_report()
        original = report.model_dump()

        render_fund_html(report)

        self.assertEqual(original, report.model_dump())

    def test_valid_report_is_saved_as_html(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "fund_brief.html"

            saved_path = save_fund_html(make_report(), output_path)

            self.assertEqual(saved_path, output_path)
            self.assertTrue(output_path.exists())
            self.assertIn("基金 006131 晨报", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
