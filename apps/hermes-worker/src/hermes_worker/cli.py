import argparse
import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from hermes_worker.core.lifespan import db_lifespan
from hermes_worker.core.logger import setup_logging
from hermes_worker.handlers.parser import build_parser


logger = logging.getLogger(__name__)

CmdHandler = Callable[[argparse.Namespace], Awaitable[None]]


async def run_app(args: argparse.Namespace) -> int:
    handler: CmdHandler | None = getattr(args, "handler", None)
    # if docker compose is used to run hermes-worker without passing any sub-command, it will default to "run-all" command.
    if handler is None:
        logger.error("unknown command: %s.", getattr(args, "command", "none"))
        return 1
    else:
        try:
            async with db_lifespan():
                await handler(args)
            return 0
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
