"""Unit and integration tests for worker job advisory locks."""

import asyncio
import pytest
from hermes_worker.jobs.locks import LOCK_KEYS, LockName, advisory_lock, lock_key
from tests.integration_utils import make_engine, require_schema


def test_lock_keys_are_stable_and_distinct() -> None:
    assert lock_key(LockName.MAINTAIN_EVENTS) == LOCK_KEYS[LockName.MAINTAIN_EVENTS]
    assert lock_key(LockName.HEALTHCHECK) == LOCK_KEYS[LockName.HEALTHCHECK]
    assert len(set(LOCK_KEYS.values())) == len(LOCK_KEYS)


def test_unknown_lock_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown job lock"):
        lock_key("maintain-nope")  # type: ignore[arg-type]


@pytest.mark.integration
def test_lock_is_exclusive_and_released() -> None:
    async def run() -> None:
        engine = make_engine()
        await require_schema(engine)
        key = lock_key(LockName.MAINTAIN_EVENTS)
        try:
            async with advisory_lock(engine, key) as first:
                assert first is True
                async with advisory_lock(engine, key) as second:
                    assert second is False
            async with advisory_lock(engine, key) as third:
                assert third is True
        finally:
            await engine.dispose()

    asyncio.run(run())
