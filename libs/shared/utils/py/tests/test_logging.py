"""Logging configuration unit tests."""

import logging
import sys

from utils_py.logging import setup_logging

EXPECTED_FORMAT = "%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s"


def test_setup_logging_configures_root_logger():
    """Configures stdout logging at INFO and silences noisy third-party loggers."""
    root = logging.getLogger()
    noisy = [logging.getLogger("sqlalchemy.engine"), logging.getLogger("httpx")]
    original_handlers = root.handlers[:]
    original_levels = [root.level, *(log.level for log in noisy)]

    try:
        root.handlers.clear()
        setup_logging()

        assert root.level == logging.INFO
        assert len(root.handlers) == 1
        handler = root.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream is sys.stdout
        assert handler.formatter is not None
        assert handler.formatter._fmt == EXPECTED_FORMAT
        assert all(log.level == logging.WARNING for log in noisy)
    finally:
        root.handlers[:] = original_handlers
        for log, level in zip([root, *noisy], original_levels, strict=True):
            log.setLevel(level)
