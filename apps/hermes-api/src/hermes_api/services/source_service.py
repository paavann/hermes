"""Source synchronization service.

Syncs the sources table in the database with a declarative
configuration file. Designed so the source-list provider can be
swapped (e.g., from a local JSON file to a remote GitOps URL)
by changing a single function.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hermes_api.db.models.source import Source

logger = logging.getLogger(__name__)

SOURCES_CONFIG_PATH = Path(__file__).resolve().parent.parent / "core" / "sources.json"


async def _load_sources_config() -> list[dict[str, Any]]:
    """Load the source list from the local JSON config file.

    This function is the single point of change for switching to a
    remote source (e.g., fetching from a raw GitHub URL or S3 bucket).
    To adopt GitOps, replace this function's body with an HTTP fetch.

    Returns:
        A list of source definition dicts.

    Raises:
        FileNotFoundError: If the config file is missing.
        json.JSONDecodeError: If the config file contains invalid JSON.
    """
    config_text = SOURCES_CONFIG_PATH.read_text(encoding="utf-8")
    data = json.loads(config_text)

    if not isinstance(data, list):
        raise ValueError(
            f"sources.json must contain a JSON array, got {type(data).__name__}."
        )

    return data


async def sync_sources_from_config(session: AsyncSession) -> dict[str, int]:
    """Synchronize the sources table with the declarative config file.

    Performs an upsert-by-slug strategy:
    - Sources in the config that don't exist in the DB are inserted.
    - Sources in the config that already exist are updated.
    - Sources in the DB whose slug is NOT in the config are soft-disabled
      (is_active = False) so their historical articles are preserved.

    Args:
        session: An async SQLAlchemy session.

    Returns:
        A dict with counts: inserted, updated, disabled.
    """
    stats = {"inserted": 0, "updated": 0, "disabled": 0}

    try:
        config_sources = await _load_sources_config()
    except FileNotFoundError:
        logger.error(
            f"sources config file not found at {SOURCES_CONFIG_PATH}. "
            "skipping source sync."
        )
        return stats
    except (json.JSONDecodeError, ValueError) as exc:
        logger.error(f"failed to parse sources config: {exc}. skipping source sync.")
        return stats

    config_slugs: set[str] = set()

    for entry in config_sources:
        slug = entry.get("slug")
        if not slug:
            logger.warning(f"skipping source entry with missing slug: {entry}")
            continue

        config_slugs.add(slug)

        stmt = select(Source).where(Source.slug == slug)
        result = await session.execute(stmt)
        existing: Optional[Source] = result.scalar_one_or_none()

        if existing:
            changed = False
            for field in ("name", "url", "feed_url", "credibility"):
                new_value = entry.get(field)
                if new_value is not None and getattr(existing, field) != new_value:
                    setattr(existing, field, new_value)
                    changed = True

            if not existing.is_active:
                existing.is_active = True
                changed = True

            if changed:
                stats["updated"] += 1
                logger.info(f"updated source: {slug}")
        else:
            source = Source(
                name=entry["name"],
                slug=slug,
                url=entry["url"],
                feed_url=entry.get("feed_url"),
                credibility=entry.get("credibility", "TIER_3"),
                is_active=True,
            )
            session.add(source)
            stats["inserted"] += 1
            logger.info(f"inserted new source: {slug}")

    # Soft-disable sources removed from the config.
    all_sources_stmt = select(Source)
    all_result = await session.execute(all_sources_stmt)
    all_sources = all_result.scalars().all()

    for source in all_sources:
        if source.slug not in config_slugs and source.is_active:
            source.is_active = False
            stats["disabled"] += 1
            logger.info(f"disabled source not in config: {source.slug}")

    await session.commit()
    logger.info(
        f"source sync complete: "
        f"{stats['inserted']} inserted, "
        f"{stats['updated']} updated, "
        f"{stats['disabled']} disabled."
    )
    return stats
