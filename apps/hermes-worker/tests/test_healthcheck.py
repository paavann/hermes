"""Unit tests for worker healthcheck schema evaluation."""

from hermes_worker.jobs.stages.healthcheck import (
    EXPECTED_COLUMNS,
    SchemaReport,
    evaluate_schema,
)


def _complete_columns() -> dict[str, set[str]]:
    return {table: set(columns) for table, columns in EXPECTED_COLUMNS.items()}


def _constraint() -> str:
    values = (
        "NEW",
        "NORMALIZED",
        "ANALYZING",
        "LABELED",
        "CLUSTERED",
        "REJECTED",
        "FAILED",
    )
    joined = ", ".join(f"'{value}'" for value in values)
    return f"CHECK (ingest_status IN ({joined}))"


def test_complete_schema_reports_ok() -> None:
    report = evaluate_schema(
        columns=_complete_columns(),
        ingest_constraint=_constraint(),
        claim_index_exists=True,
        url_identity_index_exists=True,
    )
    assert report == SchemaReport(())
    assert report.ok is True


def test_missing_columns_are_named() -> None:
    columns = _complete_columns()
    columns["articles"].discard("claimed_by")

    report = evaluate_schema(
        columns=columns,
        ingest_constraint=_constraint(),
        claim_index_exists=True,
        url_identity_index_exists=True,
    )

    assert report.ok is False
    assert report.missing == ("articles.claimed_by",)


def test_absent_table_reports_all_of_its_columns() -> None:
    columns = _complete_columns()
    del columns["articles"]

    report = evaluate_schema(
        columns=columns,
        ingest_constraint=_constraint(),
        claim_index_exists=True,
        url_identity_index_exists=True,
    )

    assert report.ok is False
    assert set(report.missing) == {
        f"articles.{column}" for column in EXPECTED_COLUMNS["articles"]
    }


def test_missing_ingest_status_values_are_reported() -> None:
    legacy = "CHECK (ingest_status IN ('NEW', 'NORMALIZED', 'LABELED'))"
    report = evaluate_schema(
        columns=_complete_columns(),
        ingest_constraint=legacy,
        claim_index_exists=True,
        url_identity_index_exists=True,
    )

    assert report.ok is False
    assert "articles.ingest_status[ANALYZING]" in report.missing
    assert "articles.ingest_status[FAILED]" in report.missing


def test_missing_constraint_is_reported() -> None:
    report = evaluate_schema(
        columns=_complete_columns(),
        ingest_constraint=None,
        claim_index_exists=True,
        url_identity_index_exists=True,
    )

    assert report.ok is False
    assert "articles.ingeststatus" in report.missing


def test_missing_claim_index_is_reported() -> None:
    report = evaluate_schema(
        columns=_complete_columns(),
        ingest_constraint=_constraint(),
        claim_index_exists=False,
        url_identity_index_exists=True,
    )

    assert report.ok is False
    assert "articles.idx_articles_analyzing_claimed_at" in report.missing


def test_missing_url_identity_index_is_reported() -> None:
    report = evaluate_schema(
        columns=_complete_columns(),
        ingest_constraint=_constraint(),
        claim_index_exists=True,
        url_identity_index_exists=False,
    )

    assert report.ok is False
    assert report.missing == ("articles.uq_articles_canonical_url_hash",)


def test_missing_source_feed_metadata_is_reported() -> None:
    columns = _complete_columns()
    columns["sources"].discard("fetch_policy")

    report = evaluate_schema(
        columns=columns,
        ingest_constraint=_constraint(),
        claim_index_exists=True,
        url_identity_index_exists=True,
    )

    assert report.ok is False
    assert report.missing == ("sources.fetch_policy",)
