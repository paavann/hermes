"""Application logging configuration."""

import logging
import sys


def setup_logging() -> None:
    """Configure root logging to emit records to stdout.

    Calls are idempotent: `logging.basicConfig` is a no-op when the root logger
    already has handlers attached. Third-party loggers that are too chatty at
    INFO level are pinned to WARNING.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
