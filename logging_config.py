from __future__ import annotations

import logging
from contextvars import ContextVar
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


LOGGER_NAME = "morning_brief"
LOG_PATH = Path(__file__).with_name("logs") / "morning_brief.log"
LOG_RETENTION_DAYS = 14
RUN_ID_CONTEXT: ContextVar[str] = ContextVar("run_id", default="-")


class RunIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = RUN_ID_CONTEXT.get()
        return True


def set_run_id(run_id: str) -> None:
    RUN_ID_CONTEXT.set(run_id)


def configure_logging(log_path: Path = LOG_PATH) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    resolved_path = str(log_path.resolve())
    has_file_handler = any(
        getattr(handler, "baseFilename", None) == resolved_path
        for handler in logger.handlers
    )
    if not has_file_handler:
        handler = TimedRotatingFileHandler(
            log_path,
            when="midnight",
            interval=1,
            backupCount=LOG_RETENTION_DAYS,
            encoding="utf-8",
        )
        handler.addFilter(RunIdFilter())
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | run_id=%(run_id)s | %(message)s"
            )
        )
        logger.addHandler(handler)

    return logger
