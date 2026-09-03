from __future__ import annotations

import json
import os

from agents import Agent, ModelSettings, function_tool
from pydantic import BaseModel, Field

from rate_agent import create_siliconflow_model
from fund_metrics import SUPPORTED_FUND_CODE, build_fund_brief


class FundBriefNarrative(BaseModel):
    """限定 Model 只能返回三段基金解释文字。"""

    summary: str = Field(
        min_length=1,
        description=(
            "只填写变化摘要：比较近5日与近20日已经发生的涨跌方向是否一致。"
            "可以写窗口名称，不要抄具体净值或百分比。"
            "这一字段不要写风险说明或申购赎回提醒。"
            "合格：近5日和近20日都在上涨，短期方向和稍长窗口一致。"
            "不合格：已启动数据调用流程，稍后基于返回结果解释。"
        ),
    )
    risk_note: str = Field(
        min_length=1,
        description=(
            "只填写风险观察：说明当前净值更靠近近期区间高点还是低点，"
            "以及最大回撤说明期间曾出现过从阶段高点向后的回落。"
            "不要抄具体数值，不要把幅度定性为温和、剧烈或可控，"
            "不要使用高位、中上、低估等未定义标签，不要写免责声明或行为提醒。"
            "合格：当前净值更靠近近期区间低点，最大回撤说明这段时间出现过一段回落。"
            "不合格：本内容不构成投资建议，基金有风险。"
        ),
    )
    behavior_reminder: str = Field(
        min_length=1,
        description=(
            "只填写行为提醒：提醒不要只根据短期涨跌决定申购、赎回或仓位。"
            "不要比较近5日与近20日，不要写风险说明，"
            "不要直接叫读者买或卖，不要复述系统要求。"
            "合格：不要只因为最近几天上涨就急着申购。"
            "不合格：请严格遵守上述指令约束，不得超出框架操作。"
        ),
    )

class FundBriefReport(BaseModel):
    """限定基金晨报最终输出的字段与取值范围。"""

    fund_code: str
    data_date: str
    age_calendar_days: int = Field(ge=0)
    freshness_basis: str
    data_status: str
    calculation_status: str

    latest_nav: float = Field(ge=0)
    change_5d_percent: float
    change_20d_percent: float
    highest_20d: float = Field(ge=0)
    lowest_20d: float = Field(ge=0)
    position_20d_percent: float = Field(ge=0, le=100)
    max_drawdown_20d_percent: float = Field(le=0)

    summary: str = Field(min_length=1)
    risk_note: str = Field(min_length=1)
    behavior_reminder: str = Field(min_length=1)


@function_tool
def get_fund_brief() -> str:
    """获取由 Python 校验并计算的基金结构化指标。"""

    brief = build_fund_brief(SUPPORTED_FUND_CODE)

    return json.dumps(brief, ensure_ascii=False)


def create_fund_brief_agent(api_key: str | None = None) -> Agent:
    """创建只解释工具结果的基金晨报 Agent。"""

    resolved_api_key = api_key or os.getenv("SILICONFLOW_API_KEY")

    if not resolved_api_key:
        raise ValueError("缺少 SILICONFLOW_API_KEY")

    return Agent(
        name="Fund Brief Agent",
        model=create_siliconflow_model(resolved_api_key),
        instructions=(
            "你为普通基金持有人写三句晨报解释。读者只会看到这三句话，"
            "不会看到任何程序说明。"
            "只根据已经返回的指标，解释已经发生的变化。"
            "summary 比较近5日与近20日的涨跌方向是否一致。"
            "risk_note 说明当前净值更靠近近期区间高点还是低点，"
            "以及最大回撤说明期间曾出现过从阶段高点向后的回落。"
            "behavior_reminder 提醒读者不要只根据短期涨跌决定申购、赎回或仓位。"
            "三段必须各自完成对应职责，不得互换或混写。"
            "可以写近5日、近20日、高点、低点；"
            "不要抄具体净值、百分比或回撤数字，"
            "不要把波动定性为温和、剧烈或可控，"
            "不要自造高位、中上、低估等标签。"
            "不要预测涨跌，不要给出买入、卖出或仓位建议，"
            "不要写调用流程、执行状态或免责声明。"
        ),
        tools=[get_fund_brief],
        model_settings=ModelSettings(tool_choice="get_fund_brief"),
        output_type=FundBriefNarrative,
    )
