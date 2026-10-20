import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TypedDict

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_db.enums import CredibilityTier, SourceType
from hermes_db.models.source import Source


logger = logging.getLogger(__name__)
DEFAULT_SOURCES_PATH = Path(__file__).resolve().parent.parent / "data" / "sources.json"


class SourceConfigEntry(TypedDict, total=False):
    slug: str
    name: str
    url: str
    feed_url: str | None
    source_type: str
    credibility: str


@dataclass(frozen=True, slots=True)
class DueSource:
    id: uuid.UUID
    name: str
    feed_url: str | None
    credibility: CredibilityTier
    fetch_interval_minutes: int = 15
    source_type: SourceType = SourceType.RSS
    url: str | None = None
    slug: str | None = None
    last_fetched_at: datetime | None = None


class SourceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_due_sources(self, force: bool = False) -> list[DueSource]:
        stmt = select(Source).where(
            Source.is_active.is_(True),
        )
        result = await self._session.execute(stmt)
        sources = result.scalars().all()

        due_sources: list[DueSource] = []
        now = datetime.now(UTC)

        for source in sources:
            if source.source_type == SourceType.RSS and not source.feed_url:
                continue

            last = source.last_fetched_at
            if last is None:
                due_sources.append(
                    DueSource(
                        id=source.id,
                        name=source.name,
                        feed_url=source.feed_url,
                        credibility=source.credibility,
                        fetch_interval_minutes=source.fetch_interval_minutes,
                        source_type=source.source_type,
                        url=source.url,
                        slug=source.slug,
                        last_fetched_at=None,
                    )
                )
                continue

            if last.tzinfo is None:
                last = last.replace(tzinfo=UTC)

            delta = timedelta(minutes=source.fetch_interval_minutes)
            if force or now >= last + delta:
                due_sources.append(
                    DueSource(
                        id=source.id,
                        name=source.name,
                        feed_url=source.feed_url,
                        credibility=source.credibility,
                        fetch_interval_minutes=source.fetch_interval_minutes,
                        source_type=source.source_type,
                        url=source.url,
                        slug=source.slug,
                        last_fetched_at=last,
                    )
                )

        return due_sources

    async def update_last_fetched(
        self, source_id: uuid.UUID, fetched_at: datetime | None = None
    ) -> None:
        now = (fetched_at or datetime.now(UTC)).replace(tzinfo=None)
        stmt = update(Source).where(Source.id == source_id).values(last_fetched_at=now)
        await self._session.execute(stmt)


async def _load_sources_config(
    config_path: Path | None = None,
) -> list[SourceConfigEntry]:
    path = config_path or DEFAULT_SOURCES_PATH
    config_text = path.read_text(encoding="utf-8")
    data = json.loads(config_text)

    if not isinstance(data, list):
        raise ValueError(
            f"sources.json must contain a JSON array, got {type(data).__name__}."
        )
    return data


async def sync_sources_from_config(
    session: AsyncSession, config_path: Path | None = None
) -> dict[str, int]:
    stats = {"inserted": 0, "updated": 0, "disabled": 0}

    try:
        config_sources = await _load_sources_config(config_path)
    except FileNotFoundError:
        logger.error("sources config file not found. skipping source sync.")
        return stats
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error("failed to load sources config: %s. skipping source sync.", exc)
        return stats

    config_slugs: set[str] = set()
    for entry in config_sources:
        slug = entry.get("slug")
        if not slug:
            logger.warning("skipping source entry with missing slug: %s.", entry)
            continue

        config_slugs.add(slug)

        stmt = select(Source).where(Source.slug == slug)
        result = await session.execute(stmt)
        existing: Source | None = result.scalar_one_or_none()
        if existing:
            changed = False
            for field in ("name", "url", "feed_url", "source_type", "credibility"):
                new_value = entry.get(field)
                if new_value is not None and getattr(existing, field) != new_value:
                    setattr(existing, field, new_value)
                    changed = True

            if not existing.is_active:
                existing.is_active = True
                changed = True

            if changed:
                stats["updated"] += 1
                logger.info("updated source: %s.", slug)
        else:
            raw_source_type = entry.get("source_type", "RSS")
            st = (
                SourceType(raw_source_type)
                if raw_source_type in SourceType.__members__
                else SourceType.RSS
            )
            raw_credibility = entry.get("credibility", "TIER_3")
            cred = (
                CredibilityTier(raw_credibility)
                if raw_credibility in CredibilityTier.__members__
                else CredibilityTier.TIER_3
            )
            source = Source(
                name=entry.get("name", slug),
                slug=slug,
                url=entry.get("url", ""),
                feed_url=entry.get("feed_url"),
                source_type=st,
                credibility=cred,
                is_active=True,
            )
            session.add(source)
            stats["inserted"] += 1
            logger.info("inserted new source: %s.", slug)

    all_sources_stmt = select(Source)
    all_result = await session.execute(all_sources_stmt)
    all_sources = all_result.scalars().all()

    for source in all_sources:
        if source.slug not in config_slugs and source.is_active:
            source.is_active = False
            stats["disabled"] += 1
            logger.info("disabled source not in config: %s.", source.slug)

    await session.commit()
    logger.info(
        "source sync complete: %s inserted, %s updated, %s disabled.",
        stats["inserted"],
        stats["updated"],
        stats["disabled"],
    )
    return stats
