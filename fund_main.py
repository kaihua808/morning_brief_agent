"""运行基金晨报 Agent，并组织 Python 工具与 Model 的输出。"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from agents import Runner
from agents.items import ToolCallOutputItem
from dotenv import load_dotenv

from fund_agent import (
    FundBriefNarrative,
    FundBriefReport,
    create_fund_brief_agent,
)
from fund_html import render_fund_html
from fund_metrics import SUPPORTED_FUND_CODE


ENV_PATH = Path(__file__).with_name(".env")
FUND_HTML_PATH = Path(__file__).with_name("output") / "fund_brief.html"


def load_api_key(env_path: Path = ENV_PATH) -> str | None:
    """从本地环境加载硅基流动 API Key，不把密钥写入源码。"""
    load_dotenv(dotenv_path=env_path, override=False)
    return os.getenv("SILICONFLOW_API_KEY")


def extract_fund_brief(run_result: Any) -> dict[str, Any]:
    """从 Agent 新产生的项目中提取基金工具返回的 JSON。"""
    for item in run_result.new_items:
        if not isinstance(item, ToolCallOutputItem) or not isinstance(item.output, str):
            continue

        try:
            brief = json.loads(item.output)
        except json.JSONDecodeError:
            continue

        if isinstance(brief, dict) and "fund_code" in brief:
            return brief

    raise ValueError("Agent 未返回有效的基金工具结果")


META_TERMS = (
    "tool",
    "get_fund_brief",
    "函数",
    "系统指令",
    "json",
    "schema",
    "根据工具",
    "工具返回",
    "工具调用",
    "调用工具",
)

METRIC_VALUE_PATTERN = re.compile(
    r"[+-]?\d+(?:\.\d+)?\s*(?:%|％|个百分点|元)"
    r"|\d+\.\d+"
)

TRADE_ADVICE_PREFIXES = (
    "建议",
    "应该",
    "应当",
    "可以",
    "适合",
    "值得",
    "立即",
    "马上",
)
TRADE_INFIXES = ("", "考虑", "用户")
TRADE_ACTIONS = (
    "买入",
    "卖出",
    "加仓",
    "减仓",
    "申购",
    "赎回",
    "清仓",
    "建仓",
)
UNSUPPORTED_QUALITATIVE_TERMS = (
    "温和",
    "不算大",
    "较小",
    "可控",
    "剧烈",
    "高位",
    "低位",
    "中上",
    "低估",
    "高估",
)
SUMMARY_REQUIRED_TERMS = ("近5日", "近20日")
RISK_POSITION_TERMS = ("高点", "低点", "区间")
RISK_DRAWDOWN_TERMS = ("最大回撤", "回撤", "回落")
BEHAVIOR_TIME_TERMS = ("短期", "单日", "最近几天", "近几天")
BEHAVIOR_DECISION_TERMS = ("申购", "赎回", "仓位", "决定", "决策")


def validate_narrative(narrative: FundBriefNarrative) -> None:
    """拦截模型解释中的元话语、具体指标值和直接交易指令。"""

    narrative_text = "\n".join(
        (
            narrative.summary,
            narrative.risk_note,
            narrative.behavior_reminder,
        )
    )
    lower_text = narrative_text.lower()

    for term in META_TERMS:
        if term in lower_text:
            raise ValueError(f"Model 解释包含元话语：{term}")

    if METRIC_VALUE_PATTERN.search(narrative_text):
        raise ValueError("Model 解释包含不应复述的具体指标值")

    for term in UNSUPPORTED_QUALITATIVE_TERMS:
        if term in narrative_text:
            raise ValueError(f"Model 解释包含无规则支持的定性标签：{term}")

    compact_text = re.sub(r"\s+", "", narrative_text)
    for prefix in TRADE_ADVICE_PREFIXES:
        for infix in TRADE_INFIXES:
            for action in TRADE_ACTIONS:
                if f"{prefix}{infix}{action}" in compact_text:
                    raise ValueError("Model 解释包含直接交易指令")

    if not all(term in narrative.summary for term in SUMMARY_REQUIRED_TERMS):
        raise ValueError("summary 未同时比较近5日与近20日")

    if not any(term in narrative.risk_note for term in RISK_POSITION_TERMS):
        raise ValueError("risk_note 未说明近期区间位置")
    if not any(term in narrative.risk_note for term in RISK_DRAWDOWN_TERMS):
        raise ValueError("risk_note 未说明最大回撤或历史回落")

    has_behavior_time = any(
        term in narrative.behavior_reminder for term in BEHAVIOR_TIME_TERMS
    )
    has_behavior_decision = any(
        term in narrative.behavior_reminder for term in BEHAVIOR_DECISION_TERMS
    )
    if not has_behavior_time or not has_behavior_decision:
        raise ValueError("behavior_reminder 未完成短期决策提醒")


def build_fund_report(
    brief: dict[str, Any],
    narrative: FundBriefNarrative,
) -> FundBriefReport:
    """合并 Python 指标和通过校验的 Model 解释。"""
    metrics = brief["metrics"]

    if not isinstance(metrics, dict):
        raise ValueError("基金指标不存在，无法生成晨报")

    return FundBriefReport(
        fund_code=brief["fund_code"],
        data_date=brief["data_date"],
        age_calendar_days=brief["age_calendar_days"],
        freshness_basis=brief["freshness_basis"],
        data_status=brief["data_status"],
        calculation_status=brief["calculation_status"],

        latest_nav=metrics["latest_nav"],
        change_5d_percent=metrics["change_5d_percent"],
        change_20d_percent=metrics["change_20d_percent"],
        highest_20d=metrics["highest_20d"],
        lowest_20d=metrics["lowest_20d"],
        position_20d_percent=metrics["position_20d_percent"],
        max_drawdown_20d_percent=metrics["max_drawdown_20d_percent"],
        summary=narrative.summary,
        risk_note=narrative.risk_note,
        behavior_reminder=narrative.behavior_reminder,
    )


def run_fund_agent(fund_code: str) -> FundBriefReport:
    """运行基金 Agent，并合并 Python 指标与 Model 解释。"""
    if fund_code != SUPPORTED_FUND_CODE:
        raise ValueError(f"当前版本只支持基金 {SUPPORTED_FUND_CODE}")

    api_key = load_api_key()
    if not api_key:
        raise ValueError("缺少 SILICONFLOW_API_KEY")

    agent = create_fund_brief_agent(api_key)
    run_result = Runner.run_sync(
        agent,
        "比较近5日与近20日，说明近期区间位置和回撤，并提醒不要只看短线。",
    )

    brief = extract_fund_brief(run_result)
    if brief.get("data_status") != "normal":
        raise ValueError(brief.get("error") or "基金数据状态异常")
    if brief.get("calculation_status") != "completed":
        raise ValueError(brief.get("error") or "基金指标计算未完成")

    narrative = run_result.final_output
    if not isinstance(narrative, FundBriefNarrative):
        narrative = FundBriefNarrative.model_validate(narrative)

    validate_narrative(narrative)

    return build_fund_report(brief, narrative)


def save_fund_html(
    report: FundBriefReport,
    output_path: Path | str = FUND_HTML_PATH,
) -> Path:
    """把通过校验的基金报告安全保存为 HTML 文件。"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")

    try:
        temporary_path.write_text(
            render_fund_html(report),
            encoding="utf-8",
        )
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    return output_path


def main() -> int:
    """接收基金代码并在终端输出 Agent 晨报 JSON。"""
    if len(sys.argv) != 2:
        print("用法：python -B fund_main.py 006131", file=sys.stderr)
        return 2

    fund_code = sys.argv[1]

    try:
        result = run_fund_agent(fund_code)
        html_path = save_fund_html(result)
    except Exception as exc:
        print(f"基金晨报生成失败：{exc}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            result.model_dump(),
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"\n基金 HTML 晨报已生成：{html_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
