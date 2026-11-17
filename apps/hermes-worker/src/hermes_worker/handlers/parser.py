import argparse
from hermes_worker.handlers.commands import (
    WorkerCmd,
    handle_all,
    handle_lifecycle,
    handle_reset_db,
    handle_sync,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-worker",
        description="Hermes Ephemeral News data ingestion & Event Lifecycle Worker",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sub_cmds = [
        (WorkerCmd.SYNC.value, "Execute RSS source sync cycle", handle_sync, True),
        (
            WorkerCmd.LIFECYCLE.value,
            "Execute event score decay and status transitions",
            handle_lifecycle,
            False,
        ),
        (
            WorkerCmd.ALL.value,
            "Execute lifecycle transitions followed by due sync",
            handle_all,
            True,
        ),
    ]
    for name, help_txt, handler, supports_force in sub_cmds:
        sub = subparsers.add_parser(name, help=help_txt)
        if supports_force:
            sub.add_argument(
                "--force",
                action="store_true",
                help="Force sync of all sources regardless of interval",
            )
        sub.set_defaults(
            handler=handler,
            sync_sources=True,
            requires_local_db=False,
        )

    reset = subparsers.add_parser(
        WorkerCmd.RESET.value,
        help="Drop all local database objects and recreate PostGIS/vector extensions",
    )
    reset.add_argument(
        "--yes",
        action="store_true",
        required=True,
        help="Required confirmation for dropping local database objects",
    )
    reset.set_defaults(
        handler=handle_reset_db,
        sync_sources=False,
        requires_local_db=True,
    )

    return parser
