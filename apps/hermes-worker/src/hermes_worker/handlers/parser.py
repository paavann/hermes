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
        sub.set_defaults(handler=handler)

    return parser
