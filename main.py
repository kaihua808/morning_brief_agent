from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from agents import Runner
from agents.items import ToolCallOutputItem
from dotenv import load_dotenv

from email_template import render_email_html
from logging_config import configure_logging, set_run_id
from rate_agent import (
    MorningBriefNarrative,
    MorningBriefReport,
    create_morning_brief_agent,
)


OUTPUT_PATH = Path(__file__).with_name("output") / "latest_report.json"
ENV_PATH = Path(__file__).with_name(".env")


def load_api_key(env_path: Path = ENV_PATH) -> str | None:
    load_dotenv(dotenv_path=env_path, override=False)
    return os.getenv("SILICONFLOW_API_KEY")


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


def build_report(
    narrative: MorningBriefNarrative,
    brief: dict[str, Any],
) -> MorningBriefReport:
    recommendation = brief["base_recommendation"]
    effective_date = brief["effective_date"]
    return MorningBriefReport(
        report_date=brief["report_date"],
        effective_rate_date=effective_date,
        usd_cny_rate=brief["usd_cny_rate"],
        usd_amount=brief["usd_amount"],
        cny_cost=brief["cny_cost"],
        observation_count=brief["observation_count"],
        position_percentile=brief["position_percentile"],
        position_label=brief["position_label"],
        trend_change_percent=brief["trend_change_percent"],
        trend_label=brief["trend_label"],
        recommendation=recommendation,
        rationale=narrative.rationale,
        email_subject=(
            f"【每日晨报】{effective_date} 汇率建议：{recommendation}"
        ),
        email_body="",
    )


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


def create_run_id() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S%z")


def save_report(report: MorningBriefReport, run_id: str) -> Path:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report_data = report.model_dump()
    report_data["run_id"] = run_id
    OUTPUT_PATH.write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return OUTPUT_PATH


def main() -> int:
    logger = configure_logging()
    run_id = create_run_id()
    set_run_id(run_id)
    logger.info("event=run_started")

    api_key = load_api_key()
    if not api_key:
        logger.error("event=config_failed reason=missing_api_key")
        print(
            "缺少SILICONFLOW_API_KEY。请通过系统环境变量或本地.env配置，"
            "不要写进源码。",
            file=sys.stderr,
        )
        return 2

    try:
        logger.info("event=model_call_started")
        morning_brief_agent = create_morning_brief_agent(api_key)
        result = Runner.run_sync(
            morning_brief_agent,
            "生成今天的晨报汇率模块，并准备可以直接发送的邮件内容。",
        )
        logger.info("event=model_call_completed")
        narrative = result.final_output
        if not isinstance(narrative, MorningBriefNarrative):
            narrative = MorningBriefNarrative.model_validate(narrative)
        brief = extract_exchange_brief(result)
        report = build_report(narrative, brief)
        logger.info("event=report_validation_started")
        validate_report(report, brief)
        logger.info("event=report_validation_completed")
        report.email_body = render_email_html(report)
        output_path = save_report(report, run_id)
        logger.info(
            "event=report_saved path=%s",
            output_path,
        )
    except Exception as exc:
        logger.exception(
            "event=run_failed error_type=%s",
            type(exc).__name__,
        )
        print(f"晨报Agent执行失败：{exc}", file=sys.stderr)
        return 1

    logger.info("event=run_completed")
    print(f"晨报已生成：{output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
