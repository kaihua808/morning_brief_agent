from __future__ import annotations

import json
import math
import os
import sys
from html import escape
from pathlib import Path
from typing import Any

from agents import Runner
from agents.items import ToolCallOutputItem

from rate_agent import MorningBriefReport, create_morning_brief_agent


OUTPUT_PATH = Path(__file__).with_name("output") / "latest_report.json"


def extract_exchange_brief(run_result: Any) -> dict[str, Any]:
    for item in run_result.new_items:
        if not isinstance(item, ToolCallOutputItem) or not isinstance(item.output, str):
            continue
        try:
            brief = json.loads(item.output)
        except json.JSONDecodeError:
            continue
        if isinstance(brief, dict) and "base_recommendation" in brief:
            return brief
    raise ValueError("Agent未调用get_exchange_brief，拒绝保存报告")


def validate_report(report: MorningBriefReport, brief: dict[str, Any]) -> None:
    expected_values = {
        "report_date": brief["report_date"],
        "effective_rate_date": brief["effective_date"],
        "usd_cny_rate": brief["usd_cny_rate"],
        "usd_amount": brief["usd_amount"],
        "cny_cost": brief["cny_cost"],
        "observation_count": brief["observation_count"],
        "position_percentile": brief["position_percentile"],
        "position_label": brief["position_label"],
        "trend_change_percent": brief["trend_change_percent"],
        "trend_label": brief["trend_label"],
        "recommendation": brief["base_recommendation"],
    }

    for field_name, expected in expected_values.items():
        actual = getattr(report, field_name)
        if isinstance(expected, float):
            matches = math.isclose(float(actual), expected, abs_tol=1e-6)
        else:
            matches = actual == expected
        if not matches:
            raise ValueError(
                f"报告字段{field_name}与工具数据不一致：{actual!r} != {expected!r}"
            )

    report_sources = [source.model_dump() for source in report.sources]
    if report_sources != brief["sources"]:
        raise ValueError("报告数据来源与工具数据不一致")


def save_report(report: MorningBriefReport) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        report.model_dump_json(indent=2),
        encoding="utf-8",
    )
    return OUTPUT_PATH


def render_email_html(report: MorningBriefReport) -> str:
    reasons = "".join(
        f'<li style="margin: 0 0 12px; line-height: 1.7;">{escape(reason)}</li>'
        for reason in report.rationale
    )
    trend_change = f"{report.trend_change_percent:+.2f}%"

    return f"""<!doctype html>
<html lang="zh-CN">
<body style="margin:0; padding:24px; background:#f5f7fa; color:#1f2937; font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;">
  <div style="max-width:640px; margin:0 auto; background:#ffffff; border:1px solid #e5e7eb; border-radius:16px; overflow:hidden;">
    <div style="padding:28px 30px 20px; border-bottom:1px solid #e5e7eb;">
      <div style="font-size:13px; color:#6b7280; margin-bottom:8px;">每日晨报 · 汇率</div>
      <div style="font-size:24px; font-weight:700;">{escape(report.effective_rate_date)}</div>
    </div>
    <div style="padding:24px 30px;">
      <div style="padding:18px 20px; margin-bottom:24px; background:#ecfdf5; border:1px solid #a7f3d0; border-radius:12px;">
        <div style="font-size:13px; color:#047857; margin-bottom:6px;">今日充值建议</div>
        <div style="font-size:22px; font-weight:700; color:#065f46;">{escape(report.recommendation)}</div>
      </div>
      <table role="presentation" style="width:100%; border-collapse:collapse; margin-bottom:26px;">
        <tr><td style="padding:11px 0; color:#6b7280; border-bottom:1px solid #f0f1f3;">USD/CNY</td><td style="padding:11px 0; text-align:right; font-weight:600; border-bottom:1px solid #f0f1f3;">{report.usd_cny_rate:.4f}</td></tr>
        <tr><td style="padding:11px 0; color:#6b7280; border-bottom:1px solid #f0f1f3;">20 美元参考成本</td><td style="padding:11px 0; text-align:right; font-weight:600; border-bottom:1px solid #f0f1f3;">¥{report.cny_cost:.2f}</td></tr>
        <tr><td style="padding:11px 0; color:#6b7280; border-bottom:1px solid #f0f1f3;">14 日位置</td><td style="padding:11px 0; text-align:right; font-weight:600; border-bottom:1px solid #f0f1f3;">{report.position_percentile:.1f}% · {escape(report.position_label)}</td></tr>
        <tr><td style="padding:11px 0; color:#6b7280;">短期趋势</td><td style="padding:11px 0; text-align:right; font-weight:600;">{escape(report.trend_label)} · {trend_change}</td></tr>
      </table>
      <div style="font-size:17px; font-weight:700; margin-bottom:14px;">判断理由</div>
      <ol style="margin:0; padding-left:22px; color:#374151;">{reasons}</ol>
    </div>
  </div>
</body>
</html>"""


def main() -> int:
    api_key = os.getenv("SILICONFLOW_API_KEY")
    if not api_key:
        print(
            "缺少SILICONFLOW_API_KEY。请先通过系统环境变量配置，不要写进代码。",
            file=sys.stderr,
        )
        return 2

    try:
        morning_brief_agent = create_morning_brief_agent(api_key)
        result = Runner.run_sync(
            morning_brief_agent,
            "生成今天的晨报汇率模块，并准备可以直接发送的邮件内容。",
        )
        report = result.final_output
        if not isinstance(report, MorningBriefReport):
            report = MorningBriefReport.model_validate(report)
        brief = extract_exchange_brief(result)
        validate_report(report, brief)
        report.email_body = render_email_html(report)
        output_path = save_report(report)
    except Exception as exc:
        print(f"晨报Agent执行失败：{exc}", file=sys.stderr)
        return 1

    print(f"晨报已生成：{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
