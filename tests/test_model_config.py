from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from agents import OpenAIChatCompletionsModel

from rate_agent import (
    MorningBriefReport,
    SILICONFLOW_BASE_URL,
    SILICONFLOW_MODEL,
    create_morning_brief_agent,
    create_siliconflow_model,
)


class SiliconFlowModelConfigTests(unittest.TestCase):
    def test_uses_chat_completions_model_and_siliconflow_endpoint(self) -> None:
        model = create_siliconflow_model("test-key")

        self.assertIsInstance(model, OpenAIChatCompletionsModel)
        self.assertEqual(model.model, SILICONFLOW_MODEL)
        self.assertEqual(
            str(model._client.base_url),
            f"{SILICONFLOW_BASE_URL}/",
        )

    def test_agent_keeps_tool_and_structured_output(self) -> None:
        agent = create_morning_brief_agent("test-key")

        self.assertIsInstance(agent.model, OpenAIChatCompletionsModel)
        self.assertEqual(len(agent.tools), 1)
        self.assertEqual(agent.model_settings.tool_choice, "get_exchange_brief")
        self.assertIs(agent.output_type, MorningBriefReport)

    def test_missing_siliconflow_key_fails_before_network_call(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "SILICONFLOW_API_KEY"):
                create_morning_brief_agent()


if __name__ == "__main__":
    unittest.main()
