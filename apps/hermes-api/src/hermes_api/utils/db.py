from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

async def delete_and_commit(session: AsyncSession, entity: Any) -> None:
    """Helper utility to delete an SQLAlchemy entity and commit the transaction."""
    await session.delete(entity)
    await session.commit()
