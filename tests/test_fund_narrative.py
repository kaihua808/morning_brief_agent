from __future__ import annotations

import unittest

from fund_agent import FundBriefNarrative
from fund_main import validate_narrative


def make_narrative(
    summary: str = "近5日与近20日的变化方向一致。",
    risk_note: str = "当前净值更靠近近期区间低点，最大回撤说明期间曾出现回落。",
    behavior_reminder: str = "不要只根据短期上涨作出申购决定。",
) -> FundBriefNarrative:
    return FundBriefNarrative(
        summary=summary,
        risk_note=risk_note,
        behavior_reminder=behavior_reminder,
    )


class FundNarrativeValidationTests(unittest.TestCase):
    def test_user_facing_analysis_is_allowed(self) -> None:
        validate_narrative(make_narrative())

    def test_redemption_impulse_reminder_is_allowed(self) -> None:
        validate_narrative(
            make_narrative(
                behavior_reminder="不要因单日下跌产生赎回冲动。",
            )
        )

    def test_bare_tool_word_in_user_language_is_allowed(self) -> None:
        validate_narrative(
            make_narrative(
                behavior_reminder="这不是交易工具，不要只根据短期上涨决定申购。",
            )
        )

    def test_program_speech_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "元话语"):
            validate_narrative(
                make_narrative(
                    summary="根据工具返回的数据，近5日与近20日方向一致。",
                )
            )

    def test_copied_percent_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "具体指标值"):
            validate_narrative(
                make_narrative(summary="近20日上涨1.82%。")
            )

    def test_copied_nav_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "具体指标值"):
            validate_narrative(
                make_narrative(risk_note="最新净值为1.1477。")
            )

    def test_direct_buy_advice_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "直接交易指令"):
            validate_narrative(
                make_narrative(behavior_reminder="建议买入。")
            )

    def test_consider_adding_position_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "直接交易指令"):
            validate_narrative(
                make_narrative(behavior_reminder="可以考虑加仓。")
            )

    def test_swapped_summary_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "summary"):
            validate_narrative(
                make_narrative(
                    summary="不要只根据短期上涨决定申购或赎回。",
                    behavior_reminder="近5日与近20日的变化方向一致。",
                )
            )

    def test_risk_note_without_drawdown_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "risk_note"):
            validate_narrative(
                make_narrative(risk_note="当前净值更靠近近期区间低点。")
            )

    def test_behavior_content_in_wrong_field_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "behavior_reminder"):
            validate_narrative(
                make_narrative(
                    behavior_reminder="近5日与近20日的变化方向一致。"
                )
            )

    def test_unsupported_volatility_label_is_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "定性标签"):
            validate_narrative(
                make_narrative(
                    risk_note=(
                        "当前净值更靠近近期区间低点，"
                        "最大回撤说明波动较为温和。"
                    )
                )
            )


if __name__ == "__main__":
    unittest.main()
