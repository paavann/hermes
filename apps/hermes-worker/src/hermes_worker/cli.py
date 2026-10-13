import argparse
import asyncio
import logging
import sys
from collections.abc import Awaitable, Callable
from hermes_worker.core.lifespan import db_lifespan
from hermes_worker.core.logger import setup_logging
from hermes_worker.handlers.commands import WorkerCmd
from hermes_worker.handlers.parser import build_parser


logger = logging.getLogger("hermes_worker")

CommandHandler = Callable[[argparse.Namespace], Awaitable[None]]


async def run_app(args: argparse.Namespace) -> int:
    handler: CommandHandler | None = getattr(args, "handler", None)
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


async def _run_command(command: str, force: bool = False) -> int:
    parser = build_parser()
    args_list = [command]
    if force and command in (WorkerCmd.SYNC.value, WorkerCmd.ALL.value):
        args_list.append("--force")
    try:
        args = parser.parse_args(args_list)
    except SystemExit:
        logger.error("unknown command: %s.", command)
        return 1
    return await run_app(args)


def main() -> None:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args()
    exit_code = asyncio.run(run_app(args))
    sys.exit(exit_code)
