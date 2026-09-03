"""使用固定可信数据生成基金 HTML 预览，不调用 Model。"""
from __future__ import annotations

from pathlib import Path

from fund_agent import FundBriefReport
from fund_html import render_fund_html


OUTPUT_PATH = Path(__file__).with_name("output") / "fund_brief_preview.html"


def build_preview_report() -> FundBriefReport:
    """创建只用于检查 HTML 布局的固定基金报告。"""
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
        summary="近5日与近20日均为上涨，两个观察窗口的方向一致。",
        risk_note=(
            "当前净值在近20日区间中更靠近低点；"
            "最大回撤说明期间曾出现从阶段高点向后的回落。"
        ),
        behavior_reminder="不要只根据最近几天的上涨就决定申购、赎回或调整仓位。",
    )


def main() -> int:
    """生成可以直接用浏览器打开的本地预览文件。"""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    html = render_fund_html(build_preview_report())
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"基金 HTML 预览已生成：{OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
