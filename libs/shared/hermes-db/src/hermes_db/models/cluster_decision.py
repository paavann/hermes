from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, Enum, Float, String, func
from sqlalchemy.orm import Mapped, mapped_column

from hermes_db.base import Base
from hermes_db.enums import ClusterDecisionKind


class ClusterDecision(Base):
    """Cached LLM adjudication for an article/event pair.

    The pair hash is the primary key, so a retry reuses the decision instead
    of paying for the same comparison twice.
    """

    __tablename__ = "cluster_decisions"

    pair_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    decision: Mapped[ClusterDecisionKind] = mapped_column(
        Enum(
            ClusterDecisionKind,
            native_enum=False,
            values_callable=lambda members: [member.value for member in members],
            name="clusterdecisionkind",
        )
    )
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0.0 AND confidence <= 1.0)",
            name="ck_cluster_decisions_confidence_range",
        ),
    )
