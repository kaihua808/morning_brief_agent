from __future__ import annotations

import argparse
import json
import sys
from logging import Logger
from pathlib import Path

from logging_config import configure_logging, set_run_id


REPORT_PATH = Path(__file__).with_name("output") / "latest_report.json"


def record_delivery(
    status: str,
    report_path: Path = REPORT_PATH,
    logger: Logger | None = None,
) -> str:
    if status not in {"sent", "failed"}:
        raise ValueError(f"不支持的邮件状态：{status}")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    run_id = report.get("run_id")
    report_date = report.get("report_date")
    if not run_id or not report_date:
        raise ValueError("报告缺少run_id或report_date，无法记录邮件状态")

    set_run_id(run_id)
    active_logger = logger or configure_logging()
    log_method = active_logger.info if status == "sent" else active_logger.error
    log_method(
        "event=email_%s report_date=%s",
        status,
        report_date,
    )
    return run_id


def main() -> int:
    parser = argparse.ArgumentParser(description="记录晨报邮件投递结果")
    parser.add_argument("status", choices=("sent", "failed"))
    args = parser.parse_args()

    logger = configure_logging()
    try:
        run_id = record_delivery(args.status, logger=logger)
    except Exception as exc:
        logger.exception(
            "event=email_delivery_log_failed status=%s error_type=%s",
            args.status,
            type(exc).__name__,
        )
        print(f"邮件状态记录失败：{exc}", file=sys.stderr)
        return 1

    print(f"邮件状态已记录：run_id={run_id} status={args.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
