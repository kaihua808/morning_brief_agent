"""从 output/latest_report.json 重建报告并渲染预览 HTML，供视觉迭代使用。

用法: python preview.py
产出: output/email_preview.html
"""
from __future__ import annotations

import json
from pathlib import Path

from email_template import render_email_html
from rate_agent import MorningBriefReport

SOURCE = Path(__file__).with_name("output") / "latest_report.json"
TARGET = Path(__file__).with_name("output") / "email_preview.html"


def main() -> int:
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    report = MorningBriefReport.model_validate(data)
    html = render_email_html(report)
    TARGET.write_text(html, encoding="utf-8")
    print(f"预览已生成：{TARGET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
