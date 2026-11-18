"""add source feed metadata and article url identity

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-19 00:00:00.000000

"""

import hashlib
from collections.abc import Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import sqlalchemy as sa
from alembic import context, op


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


FEED_PROVIDER = sa.Enum(
    "PUBLISHER",
    "GOOGLE_NEWS",
    "GDELT",
    name="sourcefeedprovider",
    native_enum=False,
)
FETCH_POLICY = sa.Enum(
    "FULL_TEXT",
    "SUMMARY_ONLY",
    name="sourcefetchpolicy",
    native_enum=False,
)

# Frozen copy of the runtime canonicalization in
# `hermes_worker/jobs/urls.py`. Migrations must not change behaviour when the
# runtime rules evolve, so the rules are inlined here instead of imported.
_TRACKING_PARAMS = frozenset(
    {
        "at_campaign",
        "at_custom1",
        "at_custom2",
        "at_medium",
        "dclid",
        "fbclid",
        "gclid",
        "igshid",
        "maca",
        "mc_cid",
        "mc_eid",
        "msclkid",
        "traffic_source",
        "utm_campaign",
        "utm_content",
        "utm_id",
        "utm_medium",
        "utm_source",
        "utm_term",
    }
)
_DEFAULT_PORTS = {"http": 80, "https": 443}


def _canonicalize_url(raw: str) -> str | None:
    candidate = raw.strip()
    if not candidate:
        return None

    try:
        parts = urlsplit(candidate)
        port = parts.port
    except ValueError:
        return None

    scheme = parts.scheme.lower()
    if scheme not in _DEFAULT_PORTS:
        return None

    host = (parts.hostname or "").lower().rstrip(".")
    if not host:
        return None

    netloc = host if port in (None, _DEFAULT_PORTS[scheme]) else f"{host}:{port}"

    path = parts.path or "/"
    if len(path) > 1:
        path = path.rstrip("/")

    kept = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in _TRACKING_PARAMS
        and not (host == "news.google.com" and key.lower() == "oc")
    ]
    kept.sort(key=lambda pair: (pair[0], pair[1]))

    return urlunsplit((scheme, netloc, path, urlencode(kept), ""))


def _url_hash(canonical_url: str) -> str:
    return hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()


def _backfill_article_hashes() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, url FROM articles ORDER BY ingested_at ASC, id ASC")
    ).all()

    winners: dict[str, object] = {}
    updates: list[dict[str, object]] = []
    for row in rows:
        canonical = _canonicalize_url(row.url)
        if canonical is None:
            continue
        digest = _url_hash(canonical)
        duplicate_of = winners.get(digest)
        if duplicate_of is None:
            winners[digest] = row.id
        updates.append(
            {
                "article_id": row.id,
                "hash": digest,
                "canonical": canonical,
                "duplicate_of": duplicate_of,
            }
        )

    if not updates:
        return

    connection.execute(
        sa.text(
            "UPDATE articles SET "
            "canonical_url_hash = :hash, "
            "canonical_url = :canonical, "
            "duplicate_of_id = :duplicate_of "
            "WHERE id = :article_id"
        ),
        updates,
    )


def upgrade() -> None:
    """Add feed metadata to sources and URL identity to articles."""
    op.add_column(
        "sources",
        sa.Column("fallback_feed_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column(
            "feed_provider",
            FEED_PROVIDER,
            server_default="PUBLISHER",
            nullable=False,
        ),
    )
    op.add_column(
        "sources",
        sa.Column("canonical_domain", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "sources",
        sa.Column(
            "paywall",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    op.add_column(
        "sources",
        sa.Column(
            "fetch_policy",
            FETCH_POLICY,
            server_default="FULL_TEXT",
            nullable=False,
        ),
    )
    op.create_index(
        "idx_sources_canonical_domain",
        "sources",
        ["canonical_domain"],
    )

    # Existing rows predate feed_provider. Classify them from the configured
    # feed host so the column is meaningful without a re-seed.
    op.execute(
        "UPDATE sources SET feed_provider = 'GOOGLE_NEWS' "
        "WHERE feed_url LIKE '%news.google.com%'"
    )
    op.execute("UPDATE sources SET feed_provider = 'GDELT' WHERE source_type = 'GDELT'")
    op.execute(
        "UPDATE sources SET canonical_domain = "
        "lower(regexp_replace("
        "split_part(split_part(split_part(url, '://', 2), '/', 1), ':', 1),"
        "'^www\\.', '')) "
        "WHERE url LIKE 'http%'"
    )

    op.add_column(
        "articles",
        sa.Column("canonical_url_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "articles",
        sa.Column("duplicate_of_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_articles_duplicate_of_id",
        "articles",
        "articles",
        ["duplicate_of_id"],
        ["id"],
        ondelete="SET NULL",
    )

    if context.is_offline_mode():
        op.execute("-- canonical_url_hash backfill needs a live connection")
    else:
        _backfill_article_hashes()

    op.create_index(
        "uq_articles_canonical_url_hash",
        "articles",
        ["canonical_url_hash"],
        unique=True,
        postgresql_where=sa.text(
            "canonical_url_hash IS NOT NULL AND duplicate_of_id IS NULL"
        ),
    )
    op.create_index(
        "idx_articles_duplicate_of_id",
        "articles",
        ["duplicate_of_id"],
    )


def downgrade() -> None:
    """Remove feed metadata and article URL identity."""
    op.drop_index("idx_articles_duplicate_of_id", table_name="articles")
    op.drop_index("uq_articles_canonical_url_hash", table_name="articles")
    op.drop_constraint("fk_articles_duplicate_of_id", "articles", type_="foreignkey")
    op.drop_column("articles", "duplicate_of_id")
    op.drop_column("articles", "canonical_url_hash")

    op.drop_index("idx_sources_canonical_domain", table_name="sources")
    op.drop_column("sources", "fetch_policy")
    op.drop_column("sources", "paywall")
    op.drop_column("sources", "canonical_domain")
    op.drop_column("sources", "feed_provider")
    op.drop_column("sources", "fallback_feed_url")
