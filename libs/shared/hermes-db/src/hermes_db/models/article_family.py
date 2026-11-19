from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hermes_db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ArticleFamily(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """A syndication family: near-identical copies of one published story.

    Families measure independence, not topic. All members of a family are
    treated as one source of evidence during verification.
    """

    __tablename__ = "article_families"

    representative_article_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("articles.id", ondelete="SET NULL"),
        nullable=True,
    )
    title_simhash: Mapped[str] = mapped_column(String(16))
    body_simhash: Mapped[str | None] = mapped_column(String(16), nullable=True)
    primary_origin_group: Mapped[str] = mapped_column(String(64))
    member_count: Mapped[int] = mapped_column(
        Integer,
        default=1,
        server_default="1",
    )

    __table_args__ = (
        CheckConstraint(
            "member_count >= 1",
            name="ck_article_families_member_count_positive",
        ),
        Index("idx_article_families_representative", "representative_article_id"),
        Index("idx_article_families_origin_group", "primary_origin_group"),
        Index("idx_article_families_updated_at", "updated_at"),
    )
