import argparse
from hermes_worker.handlers.commands import (
    WorkerCmd,
    handle_all,
    handle_lifecycle,
    handle_sync,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-worker",
        description="Hermes Ephemeral Data Sync & Event Lifecycle Worker",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run-sync.
    sync_p = subparsers.add_parser(
        WorkerCmd.SYNC.value, help="Execute RSS source sync cycle"
    )
    sync_p.add_argument(
        "--force",
        action="store_true",
        help="Force sync of all sources regardless of interval",
    )
    sync_p.set_defaults(handler=handle_sync)

    # run-lifecycle.
    lifecycle_p = subparsers.add_parser(
        WorkerCmd.LIFECYCLE.value,
        help="Execute event score decay and status transitions",
    )
    lifecycle_p.set_defaults(handler=handle_lifecycle)

    # run-all.
    all_p = subparsers.add_parser(
        WorkerCmd.ALL.value,
        help="Execute lifecycle transitions followed by due sync",
    )
    all_p.add_argument(
        "--force",
        action="store_true",
        help="Force sync of all sources regardless of interval",
    )
    all_p.set_defaults(handler=handle_all)

    return parser