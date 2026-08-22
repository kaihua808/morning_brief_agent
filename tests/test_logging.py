from __future__ import annotations

import json
import logging
import unittest
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from tempfile import TemporaryDirectory

from delivery_log import record_delivery
from logging_config import LOGGER_NAME, LOG_RETENTION_DAYS, configure_logging


class LoggingTests(unittest.TestCase):
    def tearDown(self) -> None:
        logger = logging.getLogger(LOGGER_NAME)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    def test_daily_log_rotation_and_delivery_tracking(self) -> None:
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            log_path = temp_path / "morning_brief.log"
            report_path = temp_path / "latest_report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "run_id": "20260815T093000+0800",
                        "report_date": "2026-08-15",
                    }
                ),
                encoding="utf-8",
            )

            logger = configure_logging(log_path)
            record_delivery("sent", report_path, logger)
            for handler in logger.handlers:
                handler.flush()

            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("event=email_sent", log_text)
            self.assertIn("run_id=20260815T093000+0800", log_text)

            rotating_handlers = [
                handler
                for handler in logger.handlers
                if isinstance(handler, TimedRotatingFileHandler)
            ]
            self.assertEqual(len(rotating_handlers), 1)
            self.assertEqual(
                rotating_handlers[0].backupCount,
                LOG_RETENTION_DAYS,
            )


if __name__ == "__main__":
    unittest.main()
