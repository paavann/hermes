import argparse
from hermes_worker.handlers.commands import (
    WorkerCmd,
    handle_healthcheck,
    handle_maintain_events,
    handle_reset_db,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-worker",
        description="Hermes news ingestion and event maintenance worker",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    maintain = subparsers.add_parser(
        WorkerCmd.MAINTAIN_EVENTS.value,
        help="Requeue abandoned article claims and apply event lifecycle transitions",
    )
    maintain.set_defaults(
        handler=handle_maintain_events,
        sync_sources=False,
        requires_local_db=False,
    )

    healthcheck = subparsers.add_parser(
        WorkerCmd.HEALTHCHECK.value,
        help="Check database connectivity, schema, queue depth, and stale claims",
    )
    healthcheck.set_defaults(
        handler=handle_healthcheck,
        sync_sources=False,
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
