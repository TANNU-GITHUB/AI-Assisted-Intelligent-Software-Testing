from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from input_handler.handler import session_dir


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(
            {
                "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
                "module": getattr(record, "module_name", record.name),
                "error": record.getMessage(),
            },
            ensure_ascii=False,
        )


def log_session_error(session_id: str, module: str, error: Exception | str) -> None:
    log_path = session_dir(session_id) / "logs" / "run.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(f"session-errors:{log_path.resolve()}")
    logger.setLevel(logging.ERROR)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
    logger.error(str(error), extra={"module_name": module})