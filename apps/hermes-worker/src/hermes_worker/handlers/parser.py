import argparse
from hermes_worker.handlers.commands import (
    WorkerCmd,
    handle_audit_sources,
    handle_healthcheck,
    handle_ingest_articles,
    handle_maintain_events,
    handle_reset_db,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="hermes-worker",
        description="Hermes news ingestion and event maintenance worker",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser(
        WorkerCmd.INGEST_ARTICLES.value,
        help="Fetch due sources and write the article ledger",
    )
    ingest.add_argument(
        "--force",
        action="store_true",
        help="Fetch every active source regardless of its fetch interval",
    )
    ingest.set_defaults(
        handler=handle_ingest_articles,
        requires_local_db=False,
    )

    maintain = subparsers.add_parser(
        WorkerCmd.MAINTAIN_EVENTS.value,
        help="Requeue abandoned article claims and apply event lifecycle transitions",
    )
    maintain.set_defaults(
        handler=handle_maintain_events,
        requires_local_db=False,
    )

    audit = subparsers.add_parser(
        WorkerCmd.AUDIT_SOURCES.value,
        help="Probe configured feeds and sample articles without writing to the database",
    )
    audit.set_defaults(
        handler=handle_audit_sources,
        requires_local_db=False,
        requires_db=False,
    )

    healthcheck = subparsers.add_parser(
        WorkerCmd.HEALTHCHECK.value,
        help="Check database connectivity, schema, queue depth, and stale claims",
    )
    healthcheck.set_defaults(
        handler=handle_healthcheck,
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
        requires_local_db=True,
    )

    return parser
