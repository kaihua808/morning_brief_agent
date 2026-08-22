from __future__ import annotations

import json
import os

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
    email_subject: str
    email_body: str


class MorningBriefNarrative(BaseModel):
    rationale: list[str] = Field(min_length=2, max_length=3)


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
            "你只负责输出两到三条简洁、自然的中文判断理由。"
            "不得输出或复述日期、汇率、金额、百分比、数据来源、风险提醒或邮件主题。"
            "所有确定性字段和最终HTML都由Python根据工具结果生成。"
            "position_percentile 是今日汇率在最近14个自然日有效数据中的排名位置；"
            "数值越低，20美元所需人民币通常越少。"
            "trend_label 只是最近3个交易日均值与之前3个交易日均值的对比，"
            "必须明确说明它不是未来预测。"
            "理由必须与工具返回的 position_label、trend_label 和 base_recommendation 一致。"
        ),
        tools=[get_exchange_brief],
        model_settings=ModelSettings(tool_choice="get_exchange_brief"),
        output_type=MorningBriefNarrative,
    )
