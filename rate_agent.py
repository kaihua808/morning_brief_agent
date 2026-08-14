from __future__ import annotations

import json
import os
from typing import Literal

from agents import (
    Agent,
    ModelSettings,
    OpenAIChatCompletionsModel,
    function_tool,
    set_tracing_disabled,
)
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from tools import build_exchange_brief


SILICONFLOW_BASE_URL = "https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL = "zai-org/GLM-5.2"

set_tracing_disabled(disabled=True)


class SourceInfo(BaseModel):
    name: str
    url: str
    data_date: str | None
    status: Literal["ok", "warning", "unavailable"]


class MorningBriefReport(BaseModel):
    report_date: str
    effective_rate_date: str
    usd_cny_rate: float = Field(gt=0)
    usd_amount: float = Field(gt=0)
    cny_cost: float = Field(gt=0)
    observation_count: int = Field(ge=6)
    position_percentile: float = Field(ge=0, le=100)
    position_label: str
    trend_change_percent: float
    trend_label: str
    recommendation: str
    rationale: list[str]
    warnings: list[str]
    sources: list[SourceInfo]
    email_subject: str
    email_body: str


@function_tool
def get_exchange_brief() -> str:
    """获取并分析最近14天USD/CNY数据、20美元成本和中行交叉验证。"""

    return json.dumps(build_exchange_brief(), ensure_ascii=False)


def create_siliconflow_model(api_key: str) -> OpenAIChatCompletionsModel:
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=SILICONFLOW_BASE_URL,
    )
    return OpenAIChatCompletionsModel(
        model=SILICONFLOW_MODEL,
        openai_client=client,
    )


def create_morning_brief_agent(api_key: str | None = None) -> Agent:
    resolved_api_key = api_key or os.getenv("SILICONFLOW_API_KEY")
    if not resolved_api_key:
        raise ValueError("缺少SILICONFLOW_API_KEY")

    return Agent(
        name="Morning Brief Agent",
        model=create_siliconflow_model(resolved_api_key),
        instructions=(
            "你负责生成每日中文晨报，目前只包含美元兑人民币汇率模块。"
            "必须先调用 get_exchange_brief，并严格使用工具返回的数据。"
            "不得重新计算、猜测、补写或修改工具给出的数值和三档基础结论。"
            "position_percentile 是今日汇率在最近14个自然日有效数据中的排名位置；"
            "数值越低，20美元所需人民币通常越少。"
            "trend_label 只是最近3个交易日均值与之前3个交易日均值的对比，"
            "必须明确说明它不是未来预测。"
            "recommendation 必须等于工具返回的 base_recommendation。"
            "输出简洁、自然的中文结构化结果。"
            "邮件主题格式为：【每日晨报】YYYY-MM-DD 汇率建议：结论。"
            "邮件正文只包含：数据有效日期、USD/CNY、20美元人民币参考成本、"
            "14日位置、短期趋势信号、结论和两到三条理由。"
            "邮件正文不要包含风险提醒、数据来源或免责声明，最终HTML由程序生成。"
        ),
        tools=[get_exchange_brief],
        model_settings=ModelSettings(tool_choice="get_exchange_brief"),
        output_type=MorningBriefReport,
    )
