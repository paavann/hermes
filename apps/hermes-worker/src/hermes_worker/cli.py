import argparse
import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from utils_py import setup_logging
from hermes_worker.core.config import Settings, get_settings
from hermes_worker.core.lifespan import db_lifespan
from hermes_worker.handlers.parser import build_parser
from hermes_worker.services.reset import ResetGuardError, validate_reset_target


logger = logging.getLogger(__name__)
CmdHandler = Callable[[argparse.Namespace], Awaitable[None]]
settings: Settings = get_settings()


async def run_app(args: argparse.Namespace) -> int:
    handler: CmdHandler | None = getattr(args, "handler", None)
    if handler is None:
        logger.error("unknown command: %s.", getattr(args, "command", "none"))
        return 1
    else:
        try:
            if getattr(args, "requires_local_db", False):
                validate_reset_target(
                    env=settings.ENV,
                    db_host=settings.DB_HOST,
                    db_name=settings.DB_NAME,
                )
            async with db_lifespan(sync_sources=getattr(args, "sync_sources", True)):
                await handler(args)
            return 0
        except ResetGuardError as exc:
            logger.error("%s", exc)
            return 1
        except Exception:
            logger.exception(
                "worker execution failed for command '%s'.",
                getattr(args, "command", "unknown"),
            )
            return 1


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    exit_code = asyncio.run(run_app(args))
    sys.exit(exit_code)
